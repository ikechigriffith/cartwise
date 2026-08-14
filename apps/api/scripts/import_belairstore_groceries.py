import json
import os
import re
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

SOURCE = "belairstore_web"
USD_TO_TTD_RATE = Decimal("6.78")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_price(val: Any) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val)).quantize(Decimal("0.01"))
    s = str(val).strip()
    match = re.search(r"[\d,]+(?:\.\d+)?", s)
    if match:
        clean = match.group(0).replace(",", "")
        try:
            return Decimal(clean).quantize(Decimal("0.01"))
        except Exception:
            return None
    return None


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
    name = product["title"]
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
        subcategory=product.get("category"),
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
    sku = str(product.get("sku") or product.get("id") or product["title"]).strip()
    usd_price = parse_price(product.get("price"))
    usd_regular_price = parse_price(product.get("regular_price"))

    # Convert USD prices to TTD for consistent platform-wide price comparison
    ttd_price = (usd_price * USD_TO_TTD_RATE).quantize(Decimal("0.01")) if usd_price is not None else None
    ttd_regular_price = (
        (usd_regular_price * USD_TO_TTD_RATE).quantize(Decimal("0.01"))
        if usd_regular_price is not None
        else None
    )

    package = parse_package(product["title"], price=ttd_price, retailer_payload=product)
    identity = build_product_identity(product["title"], brand=brand)
    source_url = product.get("url")

    is_on_sale = bool(product.get("is_on_sale")) or (
        ttd_regular_price is not None and ttd_price is not None and ttd_regular_price > ttd_price
    )
    promotional_tags = []
    if is_on_sale:
        promotional_tags.append("special-offer")

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
        "raw_name": product["title"],
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
        "stock_availability": "in stock",
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
        retailer = session.scalar(select(Retailer).where(Retailer.name == "Bel Air Store"))
        if not retailer:
            raise RuntimeError("Bel Air Store retailer not found. Run seed_manual_tt_stores.py first.")
        store = session.scalar(
            select(Store).where(
                Store.retailer_id == retailer.id,
                Store.external_id == "belair-marabella",
                Store.is_active.is_(True),
            )
        )
        if not store:
            store = session.scalar(select(Store).where(Store.retailer_id == retailer.id, Store.is_active.is_(True)))
        if not store:
            raise RuntimeError("No active Bel Air Store found. Run seed_manual_tt_stores.py first.")

        for product in products:
            if not product.get("title"):
                continue
            brand = product.get("brand")
            family = get_or_create_family(session, product["title"], brand=brand)
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


def load_from_raw_dir(raw_dir: str) -> list[dict[str, Any]]:
    products = []
    if not os.path.exists(raw_dir):
        return products
    for fname in os.listdir(raw_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(raw_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    products.extend(data)
                elif isinstance(data, dict):
                    if "products" in data:
                        products.extend(data["products"])
                    elif "json" in data and "products" in data["json"]:
                        products.extend(data["json"]["products"])
                    else:
                        products.append(data)
    return products


if __name__ == "__main__":
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/belairstore/raw"))
    products = load_from_raw_dir(raw_dir)
    print(f"Loaded {len(products)} products from {raw_dir}")
    if products:
        stats = import_products_data(products)
        print(json.dumps(stats, indent=2))
