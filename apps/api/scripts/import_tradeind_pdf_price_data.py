import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from sqlalchemy import select

from app.db import SessionLocal
from app.models import CanonicalProduct, ProductFamily, ProductPriceObservation, Retailer, Store
from app.package_parser import parse_package
from scripts.import_tradeind_price_data import (
    RAW_DIR,
    USER_AGENT,
    derive_retailer_name,
    discover_price_files,
    get_or_create_product,
    match_store,
    month_from_doc,
)

SOURCE = "tradeind_pdf_text"

# The 2016-2017 booklets repeat the same section layouts across pages.  The PDF
# text extractor preserves prices well, but not table geometry, so we map each
# section's columns explicitly and parse row values from right to left.
PDF_SECTION_COLUMNS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "arima barataria chaguanas couva cunupia",
        "North/Central",
        [
            ("Arima", "Xtra Foods"),
            ("Arima", "Massy Stores"),
            ("Barataria", "Food Giant"),
            ("Barataria", "Jumbo Foods"),
            ("Chaguanas", "Price Club"),
            ("Chaguanas", "Xtra Foods"),
            ("Couva", "Cash & Carry"),
            ("Couva", "Toolsie's"),
            ("Cunupia", "Low Cost"),
            ("Cunupia", "One Plus One"),
        ],
    ),
    (
        "curepe debe diego martin mayaro point fortin",
        "North/South/East/West",
        [
            ("Curepe", "Massy Stores St. Augustine"),
            ("Curepe", "Tru Valu Valpark"),
            ("Debe", "MS Food City"),
            ("Debe", "G & N"),
            ("Diego Martin", "Tru Valu"),
            ("Diego Martin", "Massy Stores"),
            ("Mayaro", "S & S Persad"),
            ("Mayaro", "Persad D' Food King"),
            ("Point Fortin", "Peiping"),
            ("Point Fortin", "Persad's"),
        ],
    ),
    (
        "port of spain princes town rio claro san fernando san juan",
        "West/South/East",
        [
            ("Port of Spain", "Back to Basics"),
            ("Port of Spain", "Payless"),
            ("Princes Town", "SNSR"),
            ("Princes Town", "Persad D' Food King"),
            ("Rio Claro", "S & S Persad"),
            ("Rio Claro", "Persad D' Food King"),
            ("San Fernando", "Food Basket"),
            ("San Fernando", "Len Hap"),
            ("San Juan", "Ramish & Leela"),
            ("San Juan", "Tru Valu"),
        ],
    ),
    (
        "sangre grande siparia fyzabad st james toco tunapuna",
        "East/South/West",
        [
            ("Sangre Grande", "Maharaj Budget Price"),
            ("Siparia/Fyzabad", "Coss Cutters"),
            ("Siparia/Fyzabad", "Stop & Shop"),
            ("St. James", "Anand Low Price"),
            ("St. James", "Tru Valu Long Circular"),
            ("Toco", "John's"),
            ("Toco", "Cumana Cooperative"),
            ("Tunapuna", "Cost Cutters"),
            ("Tunapuna", "Diskomart"),
        ],
    ),
    (
        "tobago",
        "Tobago",
        [
            ("Tobago", "Viewport"),
            ("Tobago", "Penny Savers"),
            ("Tobago", "Coss Cutters"),
            ("Tobago", "Best Buy"),
            ("Tobago", "Highlands Road"),
            ("Tobago", "Jesus Christ Makes The Difference Supermarket"),
            ("Tobago", "Bayview"),
            ("Tobago", "Pablo"),
        ],
    ),
]

# The first March 2016 booklet used a slightly different, Trinidad-only layout
# from the later 2016-2017 booklet PDFs.
OLD_PDF_SECTION_COLUMNS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "arima barataria chaguanas couva cunupia",
        "North/Central",
        [
            ("Arima", "Maharaj Westside"),
            ("Arima", "Massy Stores"),
            ("Barataria", "Food Giant"),
            ("Barataria", "Jumbo Foods"),
            ("Chaguanas", "Price Club"),
            ("Chaguanas", "Xtra Foods"),
            ("Couva", "Cash & Carry"),
            ("Couva", "Toolsie's"),
            ("Cunupia", "Low Cost"),
            ("Cunupia", "Clasic"),
        ],
    ),
    (
        "curepe debe diego martin mayaro",
        "North/South/East/West",
        [
            ("Curepe", "Maharaj Bros"),
            ("Curepe", "Tru Valu"),
            ("Debe", "MS Food City"),
            ("Debe", "G & N"),
            ("Diego Martin", "Tru Valu"),
            ("Diego Martin", "Massy Stores"),
            ("Mayaro", "S & S Persad"),
            ("Mayaro", "Persad D' Food King"),
        ],
    ),
    (
        "point fortin port of spain princes town",
        "West/South",
        [
            ("Point Fortin", "Peiping"),
            ("Point Fortin", "Winston's"),
            ("Point Fortin", "Persad's"),
            ("Point Fortin", "Massy Stores"),
            ("Port of Spain", "Back to Basics"),
            ("Port of Spain", "Payless"),
            ("Princes Town", "SNSR"),
            ("Princes Town", "Persad D' Food King"),
        ],
    ),
    (
        "rio claro san fernando san juan sangre grande",
        "South/East/West",
        [
            ("Rio Claro", "S & S Persad"),
            ("Rio Claro", "Persad D' Food King"),
            ("San Fernando", "Len Hap"),
            ("San Fernando", "Food Basket"),
            ("San Juan", "Ramesh & Leela"),
            ("San Juan", "Tru Valu"),
            ("Sangre Grande", "Maharaj"),
            ("Sangre Grande", "Economy"),
        ],
    ),
    (
        "siparia fyzabad st james toco tunapuna",
        "South/West/East",
        [
            ("Siparia/Fyzabad", "Stop & Shop"),
            ("St. James", "Anand Low Price"),
            ("St. James", "Wooling's"),
            ("Toco", "John's"),
            ("Toco", "Albert Nixon"),
            ("Toco", "Cumana Co Op"),
            ("Tunapuna", "Diskomart"),
            ("Tunapuna", "Cost Cutters"),
        ],
    ),
]

SPECIAL_PDF_OBSERVED_AT = {
    "Supermarket-Pricelist-Booklet.pdf": datetime(2016, 3, 1, tzinfo=timezone.utc),
}


def text_key(value: str) -> str:
    value = value.lower().replace("/", " ").replace(".", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def download_pdf(doc: dict[str, Any]) -> Path | None:
    url = doc["download_url"]
    if not url.lower().split("?")[0].endswith(".pdf"):
        return None
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{doc['post_id']}_{Path(urllib.parse.urlparse(url).path).name}"
    path = RAW_DIR / filename
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as response:
            path.write_bytes(response.read())
    return path


def parse_pdf_price(value: str) -> Decimal | None:
    if value == "-":
        return None
    value = value.replace("$", "").replace(",", "").strip().rstrip(".")
    if not value:
        return None
    return Decimal(value).quantize(Decimal("0.01"))


def is_value_token(token: str) -> bool:
    token = token.strip()
    return token == "-" or bool(re.fullmatch(r"\$?\d+(?:\.\d{1,2})?\.?", token))


def split_values(line: str, expected: int) -> tuple[str, list[str]] | None:
    tokens = line.replace("$ ", "$").split()
    values: list[str] = []
    while tokens and len(values) < expected:
        token = tokens[-1]
        if not is_value_token(token):
            break
        values.append(tokens.pop())
    if len(values) < max(3, expected - 2):
        return None
    values.reverse()
    if len(values) < expected:
        values = ["-"] * (expected - len(values)) + values
    return " ".join(tokens).strip(), values[-expected:]


def split_item_size(metadata: str) -> tuple[str, str | None, str | None]:
    metadata = re.sub(r"\s+", " ", metadata).strip()
    metadata = metadata.replace("–", "-")
    if not metadata:
        return "UNKNOWN", None, None
    size_match = re.search(
        r"(?i)(\b\d+(?:\.\d+)?\s?(?:kg|g|ml|l|oz|pk|pack)\b|\b\d+\s?doz\b|\b\d+x\d+g\b|\bpack\b)$",
        metadata,
    )
    size = None
    item = metadata
    if size_match:
        size = size_match.group(1).strip()
        item = metadata[: size_match.start()].strip()
    item = re.sub(r"\s+-\s*$", "", item).strip()
    # For PDF text extraction we avoid overconfident brand splitting.  The raw
    # metadata is retained in raw_payload for later product matching refinement.
    return item or metadata, None, size


def page_section(text: str) -> tuple[str, str, list[tuple[str, str]]] | None:
    key = text_key(text[:700])
    for marker, region, columns in PDF_SECTION_COLUMNS:
        if all(part in key for part in marker.split()):
            return marker, region, columns
    return None


def old_page_section(text: str) -> tuple[str, str, list[tuple[str, str]]] | None:
    key = text_key(text[:900])
    # Repair PDF text-extraction splits while keeping the canonical place names
    # above as Couva and Mayaro.
    key = key.replace("couv a", "couva").replace("may aro", "mayaro")
    for marker, region, columns in OLD_PDF_SECTION_COLUMNS:
        if all(part in key for part in marker.split()):
            return marker, region, columns
    return None


def split_old_item_brand_size(metadata: str) -> tuple[str, str | None, str | None]:
    item_with_brand, _, size = split_item_size(metadata)
    # The old booklet has explicit ITEM/BRAND/SIZE columns but PDF extraction
    # flattens them. Keep common single-token brands separated when safe; retain
    # ambiguous rows as item text rather than inventing brands.
    if not size:
        return item_with_brand, None, None
    parts = item_with_brand.rsplit(" ", 1)
    if len(parts) == 2 and re.search(r"[A-Za-z]", parts[1]) and len(parts[1]) <= 20:
        return parts[0].strip() or item_with_brand, None if parts[1] == "-" else parts[1].strip(), size
    return item_with_brand, None, size


def iter_old_pdf_rows(path: Path):
    reader = PdfReader(str(path))
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if "item" not in text.lower() or "brand" not in text.lower() or "size" not in text.lower():
            continue
        section = old_page_section(text)
        if not section:
            continue
        _, region, columns = section
        expected = len(columns)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        buffer = ""
        started = False
        started_data = False
        for line in lines:
            if not line:
                continue
            lower = line.lower()
            if "item" in lower and "brand" in lower and "size" in lower:
                started = True
                buffer = ""
                continue
            if not started:
                continue
            if lower.startswith(("pg", "consumer affairs", "ministry of trade", "section ")):
                continue
            if any(skip in lower for skip in ["maharaj westside", "massy stores", "food giant", "peiping", "s & s persad"]):
                continue
            line_has_price = any(is_value_token(token) and token != "-" for token in line.split())
            if not started_data and not line_has_price:
                continue
            started_data = True
            candidate = f"{buffer} {line}".strip() if buffer else line
            parsed = split_values(candidate, expected)
            if not parsed:
                buffer = "" if line_has_price or len(candidate) > 180 else candidate
                continue
            metadata, values = parsed
            item, brand, size = split_old_item_brand_size(metadata)
            if len(item) > 190:
                buffer = ""
                continue
            if not re.search(r"[A-Za-z]", item):
                buffer = ""
                continue
            for (area, store_label), value in zip(columns, values, strict=False):
                price = parse_pdf_price(value)
                if price is None:
                    continue
                yield {
                    "region": region,
                    "area": area,
                    "store_label": store_label,
                    "item": item,
                    "brand": brand,
                    "size": size,
                    "price": price,
                    "page": page_index,
                    "raw_metadata": metadata,
                }
            buffer = ""


def iter_pdf_rows(path: Path):
    if path.name.endswith("Supermarket-Pricelist-Booklet.pdf"):
        yield from iter_old_pdf_rows(path)
        return
    reader = PdfReader(str(path))
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if "item" not in text.lower() or "size" not in text.lower():
            continue
        section = page_section(text)
        if not section:
            continue
        _, region, columns = section
        expected = len(columns)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        buffer = ""
        started = False
        started_data = False
        for line in lines:
            if not line:
                continue
            lower = line.lower()
            if "item" in lower and "size" in lower:
                started = True
                buffer = ""
                continue
            if not started:
                continue
            if lower.startswith(("pg", "consumer affairs", "ministry of trade", "section ")):
                continue
            if any(skip in lower for skip in ["arima", "barataria", "viewport", "penny savers"]):
                continue
            line_has_price = any(is_value_token(token) and token != "-" for token in line.split())
            if not started_data and not line_has_price:
                continue
            started_data = True
            candidate = f"{buffer} {line}".strip() if buffer else line
            parsed = split_values(candidate, expected)
            if not parsed:
                # If this line already has prices but not enough columns, it is
                # usually a partial/malformed extraction row. Do not let it
                # accumulate into a later unrelated product row.
                buffer = "" if line_has_price or len(candidate) > 180 else candidate
                continue
            metadata, values = parsed
            item, brand, size = split_item_size(metadata)
            if len(item) > 190:
                buffer = ""
                continue
            if not re.search(r"[A-Za-z]", item):
                buffer = ""
                continue
            for (area, store_label), value in zip(columns, values, strict=False):
                price = parse_pdf_price(value)
                if price is None:
                    continue
                yield {
                    "region": region,
                    "area": area,
                    "store_label": store_label,
                    "item": item,
                    "brand": brand,
                    "size": size,
                    "price": price,
                    "page": page_index,
                    "raw_metadata": metadata,
                }
            buffer = ""


def get_or_create_retailer(session, name: str | None, retailer_cache: dict[str, Retailer]) -> Retailer | None:
    if not name:
        return None
    if name in retailer_cache:
        return retailer_cache[name]
    retailer = session.scalar(select(Retailer).where(Retailer.name == name))
    if not retailer:
        retailer = Retailer(name=name, integration_type="tradeind", loyalty_program_supported=False)
        session.add(retailer)
        session.flush()
    retailer_cache[name] = retailer
    return retailer


def import_pdf_docs() -> None:
    docs = discover_price_files()
    pdf_docs = []
    for doc in docs:
        filename = Path(urllib.parse.urlparse(doc["download_url"]).path).name
        observed_at = month_from_doc(doc) or SPECIAL_PDF_OBSERVED_AT.get(filename)
        if not observed_at:
            continue
        # Focus this parser on the regular text-based PDF booklet era.  Later
        # special PDFs need separate layouts/OCR treatment.
        if not (datetime(2016, 1, 1, tzinfo=observed_at.tzinfo) <= observed_at <= datetime(2017, 12, 1, tzinfo=observed_at.tzinfo)):
            continue
        if doc["download_url"].count("http") > 1:
            continue
        if doc["download_url"].lower().split("?")[0].endswith(".pdf"):
            pdf_docs.append((doc, observed_at))

    inserted = 0
    skipped_existing = 0
    matched_store = 0
    retailer_only = 0
    unmatched = 0
    parse_failures = 0
    downloaded = 0
    skipped_existing_documents = 0

    with SessionLocal() as session:
        stores = session.scalars(select(Store).where(Store.is_active.is_(True))).all()
        retailer_cache: dict[str, Retailer] = {}
        family_cache: dict[str, ProductFamily] = {}
        product_cache: dict[tuple[str, str | None], CanonicalProduct] = {}
        store_match_cache: dict[str, tuple[Store | None, float]] = {}
        seen_observations: set[tuple[str, datetime, str, str, str, str]] = set()

        for doc, observed_at in pdf_docs:
            already_imported = session.scalar(
                select(ProductPriceObservation.id).where(
                    ProductPriceObservation.source == SOURCE,
                    ProductPriceObservation.source_url == doc["download_url"],
                    ProductPriceObservation.observed_at == observed_at,
                ).limit(1)
            )
            if already_imported:
                skipped_existing_documents += 1
                continue

            try:
                path = download_pdf(doc)
                if not path:
                    continue
                downloaded += 1
                rows = list(iter_pdf_rows(path))
            except Exception as exc:
                print(f"Failed to parse {doc['download_url']}: {exc}")
                parse_failures += 1
                continue

            for row in rows:
                product = get_or_create_product(session, row["item"], row["brand"], row["size"], family_cache, product_cache)
                store_cache_key = f"{row['area']}|{row['store_label']}"
                if store_cache_key in store_match_cache:
                    store, confidence = store_match_cache[store_cache_key]
                else:
                    store, confidence = match_store(row["store_label"], stores)
                    store_match_cache[store_cache_key] = (store, confidence)

                retailer_name = derive_retailer_name(row["store_label"])
                retailer = store.retailer if store else get_or_create_retailer(session, retailer_name, retailer_cache)
                if store:
                    matched_store += 1
                elif retailer:
                    retailer_only += 1
                else:
                    unmatched += 1

                observation_key = (
                    str(product.id),
                    observed_at,
                    doc["download_url"],
                    row["region"],
                    row["area"],
                    row["store_label"],
                )
                if observation_key in seen_observations:
                    skipped_existing += 1
                    continue
                seen_observations.add(observation_key)

                existing = session.scalar(
                    select(ProductPriceObservation.id).where(
                        ProductPriceObservation.canonical_product_id == product.id,
                        ProductPriceObservation.observed_at == observed_at,
                        ProductPriceObservation.source == SOURCE,
                        ProductPriceObservation.source_url == doc["download_url"],
                        ProductPriceObservation.raw_region == row["region"],
                        ProductPriceObservation.raw_area == row["area"],
                        ProductPriceObservation.raw_store_name == row["store_label"],
                    )
                )
                if existing:
                    skipped_existing += 1
                    continue

                parsed_package = parse_package(f"{row['item']} {row['size'] or ''}", price=row["price"])
                session.add(
                    ProductPriceObservation(
                        canonical_product_id=product.id,
                        retailer_id=retailer.id if retailer else None,
                        store_id=store.id if store else None,
                        region_code="TT",
                        price=row["price"],
                        currency="TTD",
                        price_per_unit=parsed_package.computed_price_per_unit,
                        observed_at=observed_at,
                        source=SOURCE,
                        source_url=doc["download_url"],
                        raw_region=row["region"],
                        raw_area=row["area"],
                        raw_store_name=row["store_label"],
                        raw_item_name=row["item"],
                        match_confidence=confidence,
                        raw_payload={
                            **{key: (str(value) if isinstance(value, Decimal) else value) for key, value in row.items()},
                            "post_title": doc["title"],
                            "post_url": doc["post_url"],
                            "file": str(path.name),
                            "parser": "pypdf_text_section_columns_v1",
                        },
                    )
                )
                inserted += 1
            session.commit()

    print(
        json.dumps(
            {
                "discovered_pdf_documents": len(pdf_docs),
                "downloaded_pdf_documents": downloaded,
                "documents_skipped_existing": skipped_existing_documents,
                "observations_inserted": inserted,
                "observations_skipped_existing": skipped_existing,
                "matched_store_observations": matched_store,
                "retailer_only_observations": retailer_only,
                "unmatched_observations": unmatched,
                "parse_failures": parse_failures,
                "source": SOURCE,
                "raw_dir": str(RAW_DIR),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    import_pdf_docs()
