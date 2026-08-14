import json
import time
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

API_URL = "https://www.pricesmart.com/api/br_discovery/getProductsByKeyword"
CATEGORY_URL = "https://www.pricesmart.com/en-tt/category/Groceries/G10D03"
PRODUCT_URL_PREFIX = "https://www.pricesmart.com/en-tt/product/"
CATEGORY_ID = "G10D03"
ROWS = 100


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def price_from_cents(value: Any, fraction_digits: int = 2) -> Decimal | None:
    if value is None:
        return None
    return Decimal(int(value)) / (Decimal(10) ** fraction_digits)


def fetch_page(start: int) -> dict[str, Any]:
    payload = [
        {
            "url": CATEGORY_URL,
            "start": start,
            "q": CATEGORY_ID,
            "fq": [],
            "search_type": "category",
            "rows": ROWS,
            "account_id": "7024",
            "auth_key": "ev7libhybjg5h1d1",
            "request_id": int(time.time() * 1000),
            "domain_key": "pricesmart_bloomreach_io_en",
            "fl": "pid,title,price,thumb_image,brand,slug,skuid,currency,fractionDigits,master_sku,"
            "sold_by_weight_TT,weight_TT,weight_uom_description_TT,sign_price_TT,price_per_uom_TT,"
            "uom_description_TT,saving_amount_TT,original_price_without_saving_TT,availability_TT,"
            "price_TT,inventory_TT,promoid_TT",
            "view_id": "TT",
        }
    ]
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 groceries-mvp/0.1",
            "Origin": "https://www.pricesmart.com",
            "Referer": CATEGORY_URL,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all_products() -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    start = 0
    total = None
    while total is None or start < total:
        payload = fetch_page(start)
        response = payload["response"]
        total = response["numFound"]
        docs = response.get("docs", [])
        products.extend(docs)
        start += ROWS
        time.sleep(0.2)
    return products


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


def get_or_create_canonical(session, family: ProductFamily, product: dict[str, Any]) -> CanonicalProduct:
    name = product["title"]
    identity = build_product_identity(name, brand=product.get("brand"))
    canonical = session.scalar(
        select(CanonicalProduct).where(
            CanonicalProduct.canonical_name == name,
            CanonicalProduct.brand == product.get("brand"),
        )
    )
    if canonical:
        canonical.normalized_name = canonical.normalized_name or identity.normalized_name
        canonical.selection_key = canonical.selection_key or identity.selection_key
        canonical.normalized_brand = canonical.normalized_brand or identity.normalized_brand
        if canonical.size_value is None and identity.parsed_size_value is not None:
            canonical.size_value = identity.parsed_size_value
            canonical.size_unit = identity.parsed_size_unit
        if canonical.package_quantity is None and identity.parsed_package_quantity is not None:
            canonical.package_quantity = int(identity.parsed_package_quantity)
        return canonical
    canonical = CanonicalProduct(
        product_family_id=family.id,
        canonical_name=name,
        normalized_name=identity.normalized_name,
        selection_key=identity.selection_key,
        brand=product.get("brand"),
        normalized_brand=identity.normalized_brand,
        is_store_brand=(product.get("brand") == "Member's Selection"),
        owning_retailer_id=None,
        barcode=None,
        category="Groceries",
        subcategory=None,
        size_value=identity.parsed_size_value,
        size_unit=identity.parsed_size_unit,
        package_quantity=int(identity.parsed_package_quantity) if identity.parsed_package_quantity is not None else None,
        tags=product.get("promoid_TT") or [],
        requirements_supported=[],
        is_perishable=False,
    )
    session.add(canonical)
    session.flush()
    return canonical


def upsert_listing(session, store: Store, product: dict[str, Any], checked_at: datetime) -> ProductListing:
    sku = str(product.get("master_sku") or product.get("pid"))
    fraction_digits = int(product.get("fractionDigits") or 2)
    price = price_from_cents(product.get("price_TT"), fraction_digits)
    price_per_unit = price_from_cents(product.get("price_per_uom_TT"), fraction_digits)
    package = parse_package(product["title"], price=price, retailer_payload=product)
    identity = build_product_identity(product["title"], brand=product.get("brand"))
    source_url = PRODUCT_URL_PREFIX + product.get("slug", sku)

    unit_price_needs_review = package.needs_review
    if price_per_unit is not None and package.computed_price_per_unit is not None:
        diff = abs(price_per_unit - package.computed_price_per_unit)
        # Allow small rounding differences between retailer-provided and computed unit price.
        unit_price_needs_review = unit_price_needs_review or diff > Decimal("0.05")

    listing = session.scalar(
        select(ProductListing).where(
            ProductListing.store_id == store.id,
            ProductListing.retailer_product_id == sku,
            ProductListing.source == "pricesmart_api",
        )
    )
    raw_tags = product.get("promoid_TT") or []
    tags_lower = [str(t).lower() for t in raw_tags]
    orig_price_raw = product.get("original_price_without_saving_TT")
    try:
        regular_price = Decimal(str(orig_price_raw)) if orig_price_raw else None
    except Exception:
        regular_price = None

    is_sale = (
        "specialsavings" in tags_lower
        or "clearance" in tags_lower
        or "manufacturer savings" in tags_lower
        or any("saving" in t for t in tags_lower)
        or (regular_price is not None and price is not None and regular_price > price)
    )

    payload = {
        "store_id": store.id,
        "retailer_product_id": sku,
        "raw_name": product["title"],
        "normalized_name": identity.normalized_name,
        "selection_key": identity.selection_key,
        "raw_description": json.dumps(product, ensure_ascii=False),
        "raw_brand": product.get("brand"),
        "normalized_brand": identity.normalized_brand,
        "price": price,
        "is_on_sale": is_sale,
        "regular_price": regular_price,
        "promotional_tags": raw_tags,
        "sale_ends_at": None,
        "currency": "TTD",
        "price_per_unit": price_per_unit,
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
        "unit_price_needs_review": unit_price_needs_review,
        "stock_availability": product.get("inventory_TT") or product.get("availability_TT"),
        "source": "pricesmart_api",
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


def record_price_observation(session, store: Store, canonical: CanonicalProduct, listing: ProductListing, product: dict, checked_at: datetime) -> bool:
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
        source=listing.source or "pricesmart_api",
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


def import_products() -> None:
    products = fetch_all_products()
    checked_at = now_utc()

    inserted_or_updated_listings = 0
    mapped = 0
    observations = 0

    with SessionLocal() as session:
        retailer = session.scalar(select(Retailer).where(Retailer.name == "PriceSmart"))
        if not retailer:
            raise RuntimeError("PriceSmart retailer not found. Run seed_manual_tt_stores.py first.")
        stores = session.scalars(select(Store).where(Store.retailer_id == retailer.id, Store.is_active.is_(True))).all()
        if not stores:
            raise RuntimeError("No active PriceSmart stores found. Run seed_manual_tt_stores.py first.")

        for product in products:
            if not product.get("title") or not (product.get("master_sku") or product.get("pid")):
                continue
            family = get_or_create_family(session, product["title"], brand=product.get("brand"))
            canonical = get_or_create_canonical(session, family, product)
            for store in stores:
                listing = upsert_listing(session, store, product, checked_at)
                upsert_mapping(session, listing, canonical)
                record_price_observation(session, store, canonical, listing, product, checked_at)
                inserted_or_updated_listings += 1
                mapped += 1
                observations += 1
        session.commit()

    print(
        json.dumps(
            {
                "products_fetched": len(products),
                "stores": len(stores),
                "listings_inserted_or_updated": inserted_or_updated_listings,
                "mappings_inserted_or_updated": mapped,
                "observations_logged": observations,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    import_products()
