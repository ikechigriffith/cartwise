import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ProductPriceObservation, Store, now_utc
from app.package_parser import parse_package
from scripts.import_tradeind_price_data import (
    RAW_DIR,
    derive_retailer_name,
    get_or_create_product,
    get_or_create_retailer,
    iter_workbook_rows,
    match_store,
)

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def parse_file_date(filename: str) -> datetime | None:
    filename_clean = filename.lower().replace("-", " ").replace("_", " ")
    for month_name, month_num in MONTH_MAP.items():
        pattern = r"\b" + month_name + r"\b.*?(\d{4}|\d{2})\b"
        match = re.search(pattern, filename_clean)
        if match:
            yr_str = match.group(1)
            year = int(yr_str) if len(yr_str) == 4 else (2000 + int(yr_str))
            if 2018 <= year <= 2026:
                return datetime(year, month_num, 1, tzinfo=timezone.utc)
    return None


def run_import():
    files = list(RAW_DIR.glob("*.xlsx"))
    print(f"Total XLSX files found in {RAW_DIR}: {len(files)}")
    
    inserted = 0
    skipped_existing = 0
    parse_errors = 0

    with SessionLocal() as session:
        # Load caches
        family_cache = {}
        product_cache = {}
        retailer_cache = {}
        stores = session.scalars(select(Store)).all()
        store_match_cache = {}

        for index, path in enumerate(files, start=1):
            observed_at = parse_file_date(path.name)
            if not observed_at:
                print(f"[{index}/{len(files)}] Could not parse date for: {path.name}")
                continue

            try:
                rows = list(iter_workbook_rows(path))
            except Exception as e:
                print(f"[{index}/{len(files)}] Error reading {path.name}: {e}")
                parse_errors += 1
                continue

            if not rows:
                continue

            source_url = f"file://{path.name}"

            existing_keys = set(
                session.execute(
                    select(
                        ProductPriceObservation.canonical_product_id,
                        ProductPriceObservation.observed_at,
                        ProductPriceObservation.raw_region,
                        ProductPriceObservation.raw_area,
                        ProductPriceObservation.raw_store_name,
                    ).where(
                        ProductPriceObservation.source == "tradeind_xlsx",
                        ProductPriceObservation.observed_at == observed_at,
                    )
                ).all()
            )

            file_inserted = 0
            file_skipped = 0

            for row in rows:
                product = get_or_create_product(
                    session, row["item"], row["brand"], row["size"], family_cache, product_cache
                )
                store_cache_key = row["store_label"]
                if store_cache_key in store_match_cache:
                    store, confidence = store_match_cache[store_cache_key]
                else:
                    store, confidence = match_store(row["store_label"], stores)
                    store_match_cache[store_cache_key] = (store, confidence)

                retailer_name = derive_retailer_name(row["store_label"])
                retailer = (
                    store.retailer
                    if store
                    else get_or_create_retailer(session, retailer_name, retailer_cache)
                )

                obs_key = (
                    product.id,
                    observed_at,
                    row["region"],
                    row["area"],
                    row["store_label"],
                )

                if obs_key in existing_keys:
                    file_skipped += 1
                    continue

                existing_keys.add(obs_key)

                parsed = parse_package(f"{row['item']} {row['size'] or ''}", price=row["price"])
                session.add(
                    ProductPriceObservation(
                        canonical_product_id=product.id,
                        retailer_id=retailer.id if retailer else None,
                        store_id=store.id if store else None,
                        region_code="TT",
                        price=row["price"],
                        currency="TTD",
                        price_per_unit=parsed.computed_price_per_unit,
                        observed_at=observed_at,
                        source="tradeind_xlsx",
                        source_url=source_url,
                        raw_store_name=row["store_label"],
                        raw_area=row["area"],
                        raw_region=row["region"],
                        raw_item_name=row["item"],
                        raw_payload={"brand": row["brand"], "size": row["size"]},
                        created_at=now_utc(),
                        updated_at=now_utc(),
                    )
                )
                file_inserted += 1

            session.commit()
            inserted += file_inserted
            skipped_existing += file_skipped
            print(
                f"[{index}/{len(files)}] {path.name} ({observed_at.strftime('%Y-%m')}): "
                f"+{file_inserted} inserted, {file_skipped} skipped existing."
            )

    print("----------------------------------------------------------------------")
    print(f"Import Complete! Total New Observations Inserted: {inserted}")
    print(f"Total Skipped Existing Observations: {skipped_existing}")


if __name__ == "__main__":
    run_import()
