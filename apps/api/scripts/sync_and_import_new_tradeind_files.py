import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

from app.db import SessionLocal
from app.models import SourceDocument, now_utc
from scripts.import_tradeind_price_data import import_docs
from scripts.sync_tradeind_import_tracking import sync_source_documents, sync_store_candidates, write_import_run_summary

CONSUMER_AFFAIRS_URL = "https://consumeraffairs.gov.tt/supermarket-prices/"
RAW_DIR = Path("/Users/ikechi.griffith/Documents/Coding Projects/groceries/data/tradeind/raw")


def fetch_survey_links() -> list[dict[str, str]]:
    headers = {"User-Agent": "Mozilla/5.0 groceries-mvp/0.1"}
    req = urllib.request.Request(CONSUMER_AFFAIRS_URL, headers=headers)
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
    
    pattern = r"href=[\"\x27](https?://consumeraffairs\.gov\.tt/wp-content/uploads/[^\x22\x27]+\.(?:xlsx|xls|pdf))[\"\x27]"
    matches = re.findall(pattern, html, flags=re.IGNORECASE)
    unique_links = list(set(matches))
    
    results = []
    for link in unique_links:
        filename = link.split("/")[-1]
        results.append({
            "url": link,
            "filename": filename,
            "document_type": "xlsx" if filename.lower().endswith(".xlsx") else ("xls" if filename.lower().endswith(".xls") else "pdf")
        })
    return results


def download_file(url: str, target_path: Path) -> tuple[str, int]:
    headers = {"User-Agent": "Mozilla/5.0 groceries-mvp/0.1"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    return sha256, len(data)


def sync_and_download_new_files() -> dict[str, int]:
    links = fetch_survey_links()
    now = now_utc()
    downloaded = 0

    with SessionLocal() as session:
        existing_docs = {d.source_url: d for d in session.scalars(select(SourceDocument)).all()}

        for link in links:
            url = link["url"]
            filename = link["filename"]
            doc_type = link["document_type"]
            local_path = RAW_DIR / filename

            doc = existing_docs.get(url)
            if not doc:
                doc = SourceDocument(
                    source="tradeind_website",
                    source_url=url,
                    title=filename,
                    document_type=doc_type,
                    local_path=str(local_path),
                    import_status="discovered",
                    last_checked_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(doc)
                session.flush()

            if not local_path.exists() or doc.import_status == "discovered":
                try:
                    sha256, size = download_file(url, local_path)
                    doc.local_path = str(local_path)
                    doc.file_sha256 = sha256
                    doc.import_status = "downloaded"
                    doc.last_checked_at = now
                    doc.updated_at = now
                    downloaded += 1
                    print(f"Downloaded: {filename} ({size} bytes)")
                except Exception as e:
                    doc.import_status = "error"
                    doc.error_message = str(e)
                    print(f"Failed to download {filename}: {e}")

        session.commit()

    return {"discovered": len(links), "downloaded": downloaded}


if __name__ == "__main__":
    print("Fetching and downloading new Consumer Affairs survey documents...")
    res = sync_and_download_new_files()
    print(json.dumps(res, indent=2))
    
    print("\nRunning price observation import pipeline...")
    import_docs()

    print("\nSyncing store candidates...")
    candidates = sync_store_candidates()
    print("Store Candidates Synced:", candidates)
