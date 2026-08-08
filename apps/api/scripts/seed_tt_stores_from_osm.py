import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Retailer, Store

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "groceries-mvp-seed/0.1 (OpenStreetMap ODbL data)"

SHOP_PATTERN = "supermarket|convenience|greengrocer|general"

KNOWN_RETAILERS = [
    "Massy Stores",
    "Xtra Foods",
    "Tru Valu",
    "JTA Supermarkets",
    "JTA Supermarket",
    "PriceSmart",
    "Persad's D' Food King",
    "Persad D Food King",
    "SuperPharm",
    "Food Basket",
    "Pennywise",
    "Linda's Bakery",
    "National Petroleum",
    "NP Quik Shop",
    "NP Quick Shop",
]

RETAILER_ALIASES = {
    "jta": "JTA Supermarkets",
    "jta supermarket": "JTA Supermarkets",
    "jta supermarkets": "JTA Supermarkets",
    "massy": "Massy Stores",
    "massy stores": "Massy Stores",
    "tru-valu": "Tru Valu",
    "tru valu": "Tru Valu",
    "persads": "Persad's D' Food King",
    "persad's": "Persad's D' Food King",
    "persad d food king": "Persad's D' Food King",
    "persad's d' food king": "Persad's D' Food King",
    "np": "National Petroleum",
    "np quik shop": "National Petroleum",
    "np quick shop": "National Petroleum",
    "national petroleum": "National Petroleum",
}


def fetch_osm_stores() -> list[dict[str, Any]]:
    query = f'''
[out:json][timeout:90];
area["ISO3166-1"="TT"][admin_level=2]->.searchArea;
(
  node["shop"~"{SHOP_PATTERN}"](area.searchArea);
  way["shop"~"{SHOP_PATTERN}"](area.searchArea);
  relation["shop"~"{SHOP_PATTERN}"](area.searchArea);
);
out center tags;
'''
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["elements"]


def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def alias_key(value: str) -> str:
    value = clean_name(value).lower().replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_retailer_name(value: str) -> str:
    return RETAILER_ALIASES.get(alias_key(value), value)


def titleish(value: str) -> str:
    value = clean_name(value)
    if value.isupper() or value.islower():
        return value.title()
    return value


def derive_retailer_name(tags: dict[str, Any], store_name: str) -> str:
    for key in ("brand", "operator"):
        if tags.get(key):
            return normalize_retailer_name(titleish(tags[key]))

    normalized = store_name.lower()
    for retailer in KNOWN_RETAILERS:
        if retailer.lower().replace("'", "") in normalized.replace("'", ""):
            return normalize_retailer_name(retailer)

    generic_words = [
        "supermarket",
        "mini mart",
        "minimart",
        "food mart",
        "grocery",
        "groceries",
        "mart",
        "shop",
        "limited",
        "ltd",
    ]
    retailer_name = store_name
    for word in generic_words:
        retailer_name = re.sub(rf"\b{re.escape(word)}\b", "", retailer_name, flags=re.IGNORECASE)
    retailer_name = clean_name(retailer_name.strip(" -,_"))
    return normalize_retailer_name(titleish(retailer_name or store_name))


def store_type_from_shop(shop: str | None) -> str:
    if shop == "supermarket":
        return "supermarket"
    if shop == "convenience" or shop == "general":
        return "convenience"
    if shop == "greengrocer":
        return "specialty"
    return "specialty"


def extract_address(tags: dict[str, Any]) -> dict[str, Any]:
    return {
        key.removeprefix("addr:"): value
        for key, value in tags.items()
        if key.startswith("addr:") and value
    }


def extract_contact(tags: dict[str, Any]) -> dict[str, Any]:
    contact: dict[str, Any] = {}
    mapping = {
        "phone": "phone",
        "contact:phone": "phone",
        "email": "email",
        "contact:email": "email",
        "website": "website",
        "contact:website": "website",
        "facebook": "facebook",
        "contact:facebook": "facebook",
    }
    for osm_key, contact_key in mapping.items():
        if tags.get(osm_key):
            contact[contact_key] = tags[osm_key]
    return contact


def element_coordinates(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None, None


def get_or_create_retailer(session, name: str) -> Retailer:
    existing = session.scalar(select(Retailer).where(Retailer.name == name))
    if existing:
        return existing
    retailer = Retailer(name=name, integration_type="osm", loyalty_program_supported=False)
    session.add(retailer)
    session.flush()
    return retailer


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def seed() -> None:
    elements = fetch_osm_stores()
    inserted = 0
    updated = 0
    skipped = 0
    marked_missing = 0
    seen_external_ids: set[str] = set()
    refresh_time = now_utc()

    with SessionLocal() as session:
        for element in elements:
            tags = element.get("tags") or {}
            raw_name = tags.get("name")
            if not raw_name:
                skipped += 1
                continue

            lat, lon = element_coordinates(element)
            if lat is None or lon is None:
                skipped += 1
                continue

            store_name = titleish(raw_name)
            retailer_name = derive_retailer_name(tags, store_name)
            retailer = get_or_create_retailer(session, retailer_name)
            external_id = f"{element['type']}/{element['id']}"
            seen_external_ids.add(external_id)

            store = session.scalar(
                select(Store).where(Store.external_source == "osm", Store.external_id == external_id)
            )
            payload = {
                "retailer_id": retailer.id,
                "name": store_name,
                "store_type": store_type_from_shop(tags.get("shop")),
                "address": extract_address(tags),
                "latitude": lat,
                "longitude": lon,
                "contact_info": extract_contact(tags) or None,
                "service_capabilities": ["in_store"],
                "store_hours": {"opening_hours": tags["opening_hours"]} if tags.get("opening_hours") else None,
                "transit_accessibility": None,
                "external_source": "osm",
                "external_id": external_id,
                "raw_tags": tags,
                "is_active": True,
                "last_seen_at": refresh_time,
                "source_updated_at": refresh_time,
                "needs_review": False,
            }

            if store:
                for key, value in payload.items():
                    setattr(store, key, value)
                updated += 1
            else:
                session.add(Store(**payload))
                inserted += 1

        existing_osm_stores = session.scalars(select(Store).where(Store.external_source == "osm")).all()
        for store in existing_osm_stores:
            if store.external_id not in seen_external_ids:
                store.is_active = False
                store.needs_review = True
                marked_missing += 1

        session.commit()

    print(json.dumps({"inserted": inserted, "updated": updated, "skipped": skipped, "marked_missing": marked_missing}, indent=2))


if __name__ == "__main__":
    seed()
