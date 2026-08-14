import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    CanonicalProduct,
    ProductFamily,
    ProductListing,
    ProductMapping,
    ProductPriceObservation,
    Retailer,
    Store,
)
from app.package_parser import parse_package
from app.product_identity import build_product_identity

SOURCE = "westbees_doortodoor"
API_BASE_URL = "https://shop.doortodoortt.com/west/wp-json/wc/store/v1/products"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def parse_cents_to_decimal(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        cents = int(val)
        return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))
    except Exception:
        try:
            return Decimal(str(val)).quantize(Decimal("0.01"))
        except Exception:
            return None


def fetch_products_page(page: int = 1, per_page: int = 100, category_id: int | None = None) -> list[dict[str, Any]]:
    params = {"page": page, "per_page": per_page}
    if category_id:
        params["category"] = category_id
    query_str = urllib.parse.urlencode(params)
    url = f"{API_BASE_URL}?{query_str}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    ctx = create_ssl_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        if resp.status != 200:
            return []
        data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, list) else []


def get_or_create_family(session, title: str, brand: str | None = None) -> ProductFamily:
    identity = build_product_identity(title, brand=brand)
    family = session.scalar(select(ProductFamily).where(ProductFamily.name == title))
    if family:
        family.normalized_name = family.normalized_name or identity.normalized_name
        family.selection_key = family.selection_key or identity.selection_key
        return family
    family = ProductFamily(
        name=title,
        normalized_name=identity.normalized_name,
        selection_key=identity.selection_key,
        category="Groceries",
        subcategory=None,
        common_aliases=[],
        default_unit=None,
    )
    session.add(family)
    session.flush()
    return family


def get_or_create_canonical(
    session, family: ProductFamily, product: dict[str, Any], brand: str | None
) -> CanonicalProduct:
    name = product["name"]
    sku = str(product.get("sku") or "").strip() or None
    identity = build_product_identity(name, brand=brand)
    canonical = session.scalar(
        select(CanonicalProduct).where(
            CanonicalProduct.canonical_name == name,
            CanonicalProduct.brand == brand,
        )
    )
    if canonical:
        canonical.normalized_name = canonical.normalized_name or identity.normalized_name
        canonical.selection_key = canonical.selection_key or identity.selection_key
        canonical.normalized_brand = canonical.normalized_brand or identity.normalized_brand
        if not canonical.barcode and sku:
            canonical.barcode = sku
        if canonical.size_value is None and identity.parsed_size_value is not None:
            canonical.size_value = identity.parsed_size_value
            canonical.size_unit = identity.parsed_size_unit
        if canonical.package_quantity is None and identity.parsed_package_quantity is not None:
            canonical.package_quantity = int(identity.parsed_package_quantity)
        return canonical

    primary_cat = None
    cats = product.get("categories") or []
    if cats and isinstance(cats, list):
        primary_cat = cats[0].get("name") if isinstance(cats[0], dict) else str(cats[0])

    canonical = CanonicalProduct(
        product_family_id=family.id,
        canonical_name=name,
        normalized_name=identity.normalized_name,
        selection_key=identity.selection_key,
        brand=brand,
        normalized_brand=identity.normalized_brand,
        is_store_brand=False,
        owning_retailer_id=None,
        barcode=sku,
        category="Groceries",
        subcategory=primary_cat,
        size_value=identity.parsed_size_value,
        size_unit=identity.parsed_size_unit,
        package_quantity=int(identity.parsed_package_quantity) if identity.parsed_package_quantity is not None else None,
        tags=[],
        requirements_supported=[],
        is_perishable=False,
    )
    session.add(canonical)
    session.flush()
    return canonical


def upsert_listing(
    session,
    store: Store,
    product: dict[str, Any],
    brand: str | None,
    checked_at: datetime,
) -> ProductListing:
    product_id = str(product.get("id"))
    sku = str(product.get("sku") or product_id).strip()
    prices = product.get("prices") or {}

    ttd_price = parse_cents_to_decimal(prices.get("price"))
    ttd_regular_price = parse_cents_to_decimal(prices.get("regular_price"))

    package = parse_package(product["name"], price=ttd_price, retailer_payload=product)
    identity = build_product_identity(product["name"], brand=brand)
    source_url = product.get("permalink")

    is_on_sale = bool(product.get("on_sale")) or (
        ttd_regular_price is not None and ttd_price is not None and ttd_regular_price > ttd_price
    )
    promotional_tags = []
    if is_on_sale:
        promotional_tags.append("special-offer")

    is_in_stock = product.get("is_in_stock", True)
    stock_status = "in stock" if is_in_stock else "out of stock"

    listing = session.scalar(
        select(ProductListing).where(
            ProductListing.store_id == store.id,
            ProductListing.retailer_product_id == sku,
            ProductListing.source == SOURCE,
        )
    )

    payload = {
        "store_id": store.id,
        "retailer_product_id": sku,
        "raw_name": product["name"],
        "normalized_name": identity.normalized_name,
        "selection_key": identity.selection_key,
        "raw_description": json.dumps(product, ensure_ascii=False),
        "raw_brand": brand,
        "normalized_brand": identity.normalized_brand,
        "price": ttd_price,
        "is_on_sale": is_on_sale,
        "regular_price": ttd_regular_price,
        "promotional_tags": promotional_tags,
        "sale_ends_at": None,
        "currency": "TTD",
        "price_per_unit": package.computed_price_per_unit,
        "package_quantity": package.package_quantity,
        "unit_size_value": package.unit_size_value,
        "unit_size_unit": package.unit_size_unit,
        "total_size_value": package.total_size_value,
        "total_size_unit": package.total_size_unit,
        "normalized_size_value": package.normalized_size_value,
        "normalized_size_unit": package.normalized_size_unit,
        "computed_price_per_unit": package.computed_price_per_unit,
        "computed_price_unit": package.computed_price_unit,
        "unit_price_confidence": package.confidence,
        "unit_price_needs_review": package.needs_review,
        "stock_availability": stock_status,
        "source": SOURCE,
        "source_url": source_url,
        "price_checked_at": checked_at,
        "stock_checked_at": checked_at,
    }

    if listing:
        for key, value in payload.items():
            setattr(listing, key, value)
        return listing

    listing = ProductListing(**payload)
    session.add(listing)
    session.flush()
    return listing


def upsert_mapping(session, listing: ProductListing, canonical: CanonicalProduct) -> None:
    mapping = session.scalar(
        select(ProductMapping).where(
            ProductMapping.product_listing_id == listing.id,
            ProductMapping.canonical_product_id == canonical.id,
        )
    )
    if mapping:
        mapping.confidence = 1.0
        mapping.confidence_level = "high"
        mapping.mapping_method = "retailer_sku"
        mapping.status = "approved"
        return
    session.add(
        ProductMapping(
            product_listing_id=listing.id,
            canonical_product_id=canonical.id,
            confidence=1.0,
            confidence_level="high",
            mapping_method="retailer_sku",
            status="approved",
        )
    )


def record_price_observation(
    session, store: Store, canonical: CanonicalProduct, listing: ProductListing, product: dict, checked_at: datetime
) -> bool:
    if listing.price is None:
        return False
    now = now_utc()
    obs = ProductPriceObservation(
        canonical_product_id=canonical.id,
        retailer_id=store.retailer_id,
        store_id=store.id,
        region_code="TT",
        price=listing.price,
        is_on_sale=listing.is_on_sale,
        regular_price=listing.regular_price,
        promotional_tags=listing.promotional_tags,
        currency=listing.currency or "TTD",
        price_per_unit=listing.computed_price_per_unit,
        observed_at=checked_at,
        source=listing.source or SOURCE,
        source_url=listing.source_url,
        raw_store_name=store.name,
        raw_item_name=listing.raw_name,
        match_confidence=1.0,
        raw_payload=product if isinstance(product, dict) else {},
        created_at=now,
        updated_at=now,
    )
    session.add(obs)
    return True


def import_products_data(products: list[dict[str, Any]]) -> dict[str, int]:
    checked_at = now_utc()
    inserted_or_updated = 0
    mapped = 0
    observations = 0

    with SessionLocal() as session:
        retailer = session.scalar(select(Retailer).where(Retailer.name == "West Bees"))
        if not retailer:
            raise RuntimeError("West Bees retailer not found.")
        store = session.scalar(select(Store).where(Store.retailer_id == retailer.id, Store.is_active.is_(True)))
        if not store:
            raise RuntimeError("No active West Bees store found.")

        for product in products:
            if not product.get("name"):
                continue
            brand = None  # Brand extraction via package/identity
            family = get_or_create_family(session, product["name"], brand=brand)
            canonical = get_or_create_canonical(session, family, product, brand)
            listing = upsert_listing(session, store, product, brand, checked_at)
            upsert_mapping(session, listing, canonical)
            record_price_observation(session, store, canonical, listing, product, checked_at)
            inserted_or_updated += 1
            mapped += 1
            observations += 1

        session.commit()

    return {
        "products_processed": len(products),
        "listings_inserted_or_updated": inserted_or_updated,
        "mappings_inserted_or_updated": mapped,
        "observations_logged": observations,
    }


def main():
    parser = argparse.ArgumentParser(description="Import West Bees grocery products from Door to Door API")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to crawl (100 items per page)")
    parser.add_argument("--per-page", type=int, default=100, help="Products per page")
    parser.add_argument("--raw-dir", type=str, default=None, help="Directory to save/load raw JSON files")
    args = parser.parse_args()

    raw_dir = args.raw_dir or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../data/westbees/raw")
    )
    os.makedirs(raw_dir, exist_ok=True)

    print(f"Fetching {args.pages} pages ({args.per_page} items/page) from Door to Door Westbees API...")
    all_products = []
    for page in range(1, args.pages + 1):
        print(f"  Fetching page {page}...")
        try:
            items = fetch_products_page(page=page, per_page=args.per_page)
            if not items:
                print(f"  Page {page} returned no items. Stopping.")
                break
            all_products.extend(items)
            print(f"  Retrieved {len(items)} items from page {page}.")
            
            # Save raw page
            page_path = os.path.join(raw_dir, f"page_{page}.json")
            with open(page_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    print(f"Total products retrieved: {len(all_products)}")
    if all_products:
        stats = import_products_data(all_products)
        print("Import Results:")
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
