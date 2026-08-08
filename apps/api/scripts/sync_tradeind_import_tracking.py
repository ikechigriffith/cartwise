import hashlib
import json
import urllib.parse
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ImportRun, ProductPriceObservation, SourceDocument, StoreCandidate
from scripts.import_tradeind_price_data import RAW_DIR, discover_price_files, month_from_doc, normalize, now_utc

TRADEIND_SOURCES = {"tradeind_xlsx", "tradeind_pdf_text"}


def document_type(url: str) -> str | None:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower().lstrip(".")
    return suffix or None


def local_path_for_doc(doc: dict[str, Any]) -> Path:
    return RAW_DIR / f"{doc['post_id']}_{Path(urllib.parse.urlparse(doc['download_url']).path).name}"


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sync_source_documents() -> int:
    docs = discover_price_files()
    now = now_utc()
    upserted = 0
    seen_urls: set[str] = set()
    with SessionLocal() as session:
        for doc in docs:
            url = doc["download_url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            path = local_path_for_doc(doc)
            observed_at = month_from_doc(doc)
            observations_count = session.scalar(
                select(func.count(ProductPriceObservation.id)).where(ProductPriceObservation.source_url == url)
            )
            source_doc = session.scalar(select(SourceDocument).where(SourceDocument.source_url == url))
            if not source_doc:
                source_doc = SourceDocument(source="tradeind", source_url=url, created_at=now, updated_at=now)
                session.add(source_doc)
            source_doc.title = doc.get("title")
            source_doc.post_id = str(doc.get("post_id")) if doc.get("post_id") is not None else None
            source_doc.post_url = doc.get("post_url")
            source_doc.document_type = document_type(url)
            source_doc.observed_at = observed_at
            source_doc.local_path = str(path) if path.exists() else None
            source_doc.file_sha256 = sha256(path)
            source_doc.last_checked_at = now
            source_doc.observations_count = observations_count or 0
            source_doc.import_status = "imported" if observations_count else "discovered"
            source_doc.imported_at = now if observations_count else source_doc.imported_at
            source_doc.source_metadata = {"post_id": doc.get("post_id")}
            source_doc.updated_at = now
            upserted += 1
        session.commit()
    return upserted


def sync_store_candidates() -> int:
    now = now_utc()
    rows_synced = 0
    with SessionLocal() as session:
        rows = session.execute(
            select(
                ProductPriceObservation.raw_store_name,
                ProductPriceObservation.raw_area,
                ProductPriceObservation.raw_region,
                ProductPriceObservation.retailer_id,
                func.count(ProductPriceObservation.id),
                func.min(ProductPriceObservation.observed_at),
                func.max(ProductPriceObservation.observed_at),
                func.count(func.distinct(ProductPriceObservation.source_url)),
                func.max(ProductPriceObservation.match_confidence),
            )
            .where(
                ProductPriceObservation.source.in_(TRADEIND_SOURCES),
                ProductPriceObservation.raw_store_name.is_not(None),
                ProductPriceObservation.store_id.is_(None),
            )
            .group_by(
                ProductPriceObservation.raw_store_name,
                ProductPriceObservation.raw_area,
                ProductPriceObservation.raw_region,
                ProductPriceObservation.retailer_id,
            )
        ).all()

        for raw_store_name, raw_area, raw_region, retailer_id, count, first_seen, last_seen, source_docs, confidence in rows:
            candidate = session.scalar(
                select(StoreCandidate).where(
                    StoreCandidate.source == "tradeind",
                    StoreCandidate.raw_store_name == raw_store_name,
                    StoreCandidate.raw_area == raw_area,
                    StoreCandidate.raw_region == raw_region,
                )
            )
            if not candidate:
                candidate = StoreCandidate(
                    source="tradeind",
                    raw_store_name=raw_store_name,
                    raw_area=raw_area,
                    raw_region=raw_region,
                    normalized_name=normalize(raw_store_name),
                    status="needs_review",
                    created_at=now,
                    updated_at=now,
                )
                session.add(candidate)
            candidate.normalized_name = normalize(raw_store_name)
            candidate.retailer_id = retailer_id or candidate.retailer_id
            candidate.confidence = float(confidence) if confidence is not None else None
            candidate.observations_count = count or 0
            candidate.first_seen_at = first_seen
            candidate.last_seen_at = last_seen
            candidate.evidence = {
                "source_documents_count": source_docs,
                "source": "product_price_observations",
                "requires_location_verification": True,
            }
            candidate.updated_at = now
            rows_synced += 1
        session.commit()
    return rows_synced


def write_import_run_summary(source_documents: int, store_candidates: int) -> None:
    now = now_utc()
    with SessionLocal() as session:
        summary = session.execute(
            select(
                func.count(ProductPriceObservation.id),
                func.count(func.distinct(ProductPriceObservation.source_url)),
                func.count().filter(ProductPriceObservation.store_id.is_not(None)),
                func.count().filter(ProductPriceObservation.store_id.is_(None), ProductPriceObservation.retailer_id.is_not(None)),
                func.count().filter(ProductPriceObservation.store_id.is_(None), ProductPriceObservation.retailer_id.is_(None)),
            ).where(ProductPriceObservation.source.in_(TRADEIND_SOURCES))
        ).one()
        session.add(
            ImportRun(
                source="tradeind_tracking_sync",
                status="completed",
                started_at=now,
                ended_at=now,
                discovered_documents=source_documents,
                downloaded_documents=summary[1] or 0,
                observations_inserted=0,
                observations_skipped=0,
                matched_store_observations=summary[2] or 0,
                retailer_only_observations=summary[3] or 0,
                unmatched_observations=summary[4] or 0,
                raw_summary={
                    "total_tradeind_observations": summary[0] or 0,
                    "source_documents_synced": source_documents,
                    "store_candidates_synced": store_candidates,
                    "note": "Tracking/review sync over already-imported TradeInd observations; not a data import run.",
                },
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


def main() -> None:
    source_documents = sync_source_documents()
    store_candidates = sync_store_candidates()
    write_import_run_summary(source_documents, store_candidates)
    print(json.dumps({"source_documents_synced": source_documents, "store_candidates_synced": store_candidates}, indent=2))


if __name__ == "__main__":
    main()
