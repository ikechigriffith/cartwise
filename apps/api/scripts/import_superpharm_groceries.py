import json
import re
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
    RetailerDataSource,
    Store,
)
from app.package_parser import parse_package
from app.product_identity import build_product_identity

SITE_URL = "https://superpharmtt.com"
API_URL = "https://api.superpharmtt.com/api"
SOURCE = "superpharm_api"
GROCERY_CATEGORY_ID = "546"
APP_ID = "1"
LANGUAGE_ID = "EN-TT"
PAGE_SIZE = 100
FALLBACK_APP_VERSION = "2026.08.04.#2647"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def request_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{API_URL}/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": SITE_URL,
            "Referer": f"{SITE_URL}/",
            "User-Agent": "Mozilla/5.0 groceries-mvp/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_app_version() -> str:
    try:
        req = urllib.request.Request(f"{SITE_URL}/", headers={"User-Agent": "Mozilla/5.0 groceries-mvp/0.1"})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")
        matches = re.findall(r"20\d{2}\.\d{2}\.\d{2}\.#\d+", html)
        return matches[-1] if matches else FALLBACK_APP_VERSION
    except Exception:
        return FALLBACK_APP_VERSION


def common_payload(app_version: str) -> dict[str, str]:
    return {"appversion": app_version, "appID": APP_ID, "languageID": LANGUAGE_ID}


def fetch_stores(app_version: str) -> list[dict[str, Any]]:
    return request_json("service/GetStores", common_payload(app_version)).get("stores", [])


def fetch_grocery_subcategories(app_version: str) -> list[dict[str, Any]]:
    data = request_json("service/GetProductsHierarchy", common_payload(app_version))
    categories = data.get("productsHierarchy", {}).get("categories", [])
    grocery = next((category for category in categories if str(category.get("nodeId")) == GROCERY_CATEGORY_ID), None)
    if not grocery:
        raise RuntimeError("SuperPharm grocery category was not found")
    return grocery.get("subcategories", [])


def fetch_products(app_version: str, subcategories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products_by_sku: dict[str, dict[str, Any]] = {}
    for subcategory in subcategories:
        category_id = str(subcategory["nodeId"])
        page_index = 0
        while True:
            payload = {
                "categoryId": category_id,
                "pageIdx": page_index,
                "pageSize": PAGE_SIZE,
                "storeNo": "",
                **common_payload(app_version),
            }
            data = request_json("search/GetProducts", payload)
            products = data.get("products", [])
            for product in products:
                sku = str(product.get("productNumber") or "").strip()
                if sku:
                    products_by_sku[sku] = product
            pages_total = int(data.get("pagesTotal") or 0)
            page_index += 1
            if not products or page_index >= pages_total:
                break
    return list(products_by_sku.values())


def product_brand(product: dict[str, Any]) -> str | None:
    for attribute in product.get("attributesValues") or []:
        if attribute.get("attributeCode") == "BRAND":
            value = str(attribute.get("attributeValue") or "").strip()
            return value.title() if value else None
    return None


def product_name(product: dict[str, Any]) -> str:
    return str(product.get("productTitle") or product.get("productName") or "").strip()


def upsert_retailer(session) -> Retailer:
    retailer = session.scalar(select(Retailer).where(Retailer.name == "SuperPharm"))
    if not retailer:
        retailer = Retailer(
            name="SuperPharm",
            website_url=SITE_URL,
            integration_type="api",
            loyalty_program_supported=True,
        )
        session.add(retailer)
        session.flush()
    else:
        retailer.website_url = SITE_URL
        retailer.integration_type = "api"

    source = session.scalar(
        select(RetailerDataSource).where(
            RetailerDataSource.retailer_id == retailer.id,
            RetailerDataSource.source_url == f"{SITE_URL}/",
        )
    )
    if source:
        source.source_type = "api"
        source.has_product_catalog = True
        source.has_prices = True
        source.has_stock = True
        source.requires_login = False
        source.scrape_status = "active"
        source.confidence = "high"
        source.last_checked_at = now_utc()
        source.notes = "Public SuperPharm application API provides products, TTD prices, and store-level availability."
    return retailer


def upsert_stores(session, retailer: Retailer, api_stores: list[dict[str, Any]], checked_at: datetime) -> dict[str, Store]:
    stores_by_code: dict[str, Store] = {}
    for item in api_stores:
        code = str(item.get("number") or "").strip()
        if not code:
            continue
        store = session.scalar(
            select(Store).where(Store.external_source == SOURCE, Store.external_id == code)
        )
        schedule = item.get("workingSchedule")
        payload = {
            "retailer_id": retailer.id,
            "name": f"SuperPharm {item.get('name') or code}",
            "store_type": "specialty",
            "address": {
                "formatted": item.get("address"),
                "city": item.get("city"),
                "country": "Trinidad and Tobago",
            },
            "latitude": float(item["lat"]),
            "longitude": float(item["lng"]),
            "contact_info": {"phone": item.get("phoneNumber"), "website": SITE_URL},
            "service_capabilities": ["in_store", "pickup", "delivery"],
            "store_hours": schedule,
            "transit_accessibility": None,
            "external_source": SOURCE,
            "external_id": code,
            "raw_tags": {"superpharm_store": item},
            "is_active": True,
            "last_seen_at": checked_at,
            "source_updated_at": checked_at,
            "needs_review": False,
            "verified_at": checked_at,
        }
        if store:
            for key, value in payload.items():
                setattr(store, key, value)
        else:
            store = Store(**payload)
            session.add(store)
            session.flush()
        stores_by_code[code] = store
    return stores_by_code


def get_or_create_family(session, name: str, brand: str | None, subcategory: str | None) -> ProductFamily:
    identity = build_product_identity(name, brand=brand)
    family = session.scalar(select(ProductFamily).where(ProductFamily.name == name))
    if family:
        family.normalized_name = family.normalized_name or identity.normalized_name
        family.selection_key = family.selection_key or identity.selection_key
        family.category = family.category or "Groceries"
        family.subcategory = family.subcategory or subcategory
        return family
    family = ProductFamily(
        name=name,
        normalized_name=identity.normalized_name,
        selection_key=identity.selection_key,
        category="Groceries",
        subcategory=subcategory,
        common_aliases=[],
        default_unit=None,
    )
    session.add(family)
    session.flush()
    return family


def get_or_create_canonical(
    session, family: ProductFamily, product: dict[str, Any], name: str, brand: str | None
) -> CanonicalProduct:
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
        barcode=None,
        category="Groceries",
        subcategory=product.get("subCategoryName"),
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
    name: str,
    brand: str | None,
    checked_at: datetime,
) -> ProductListing:
    sku = str(product["productNumber"])
    price = Decimal(str(product["price"])).quantize(Decimal("0.01")) if product.get("price") is not None else None
    package = parse_package(name, price=price, retailer_payload=product)
    identity = build_product_identity(name, brand=brand)
    available_codes = {str(code) for code in product.get("availableAtStores") or []}
    in_stock = store.external_id in available_codes and bool(product.get("available", True))
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
        "raw_name": name,
        "normalized_name": identity.normalized_name,
        "selection_key": identity.selection_key,
        "raw_description": json.dumps(product, ensure_ascii=False),
        "raw_brand": brand,
        "normalized_brand": identity.normalized_brand,
        "price": price,
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
        "stock_availability": "in stock" if in_stock else "out of stock",
        "source": SOURCE,
        "source_url": f"{SITE_URL}/products/{sku}",
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


def import_products() -> None:
    app_version = fetch_app_version()
    api_stores = fetch_stores(app_version)
    subcategories = fetch_grocery_subcategories(app_version)
    products = fetch_products(app_version, subcategories)
    checked_at = now_utc()
    listings_upserted = 0
    mappings_upserted = 0
    observations_logged = 0
    stale_listings = 0

    with SessionLocal() as session:
        retailer = upsert_retailer(session)
        stores_by_code = upsert_stores(session, retailer, api_stores, checked_at)
        for product in products:
            name = product_name(product)
            sku = str(product.get("productNumber") or "").strip()
            if not name or not sku:
                continue
            brand = product_brand(product)
            family = get_or_create_family(session, name, brand, product.get("subCategoryName"))
            canonical = get_or_create_canonical(session, family, product, name, brand)
            for store in stores_by_code.values():
                listing = upsert_listing(session, store, product, name, brand, checked_at)
                upsert_mapping(session, listing, canonical)
                record_price_observation(session, store, canonical, listing, product, checked_at)
                listings_upserted += 1
                mappings_upserted += 1
                observations_logged += 1

        old_listings = session.scalars(
            select(ProductListing).where(
                ProductListing.source == SOURCE,
                ProductListing.price_checked_at < checked_at,
            )
        ).all()
        for listing in old_listings:
            listing.stock_availability = "out of stock"
            listing.stock_checked_at = checked_at
            stale_listings += 1
        session.commit()

    print(
        json.dumps(
            {
                "app_version": app_version,
                "grocery_subcategories": len(subcategories),
                "products_fetched": len(products),
                "stores": len(api_stores),
                "listings_inserted_or_updated": listings_upserted,
                "mappings_inserted_or_updated": mappings_upserted,
                "stale_listings_marked_out_of_stock": stale_listings,
                "source": SOURCE,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    import_products()
