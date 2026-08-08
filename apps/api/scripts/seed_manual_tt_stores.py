from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Retailer, Store


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


MANUAL_STORES = [
    {
        "retailer": "PriceSmart",
        "retailer_website": "https://www.pricesmart.com/site/tt/en",
        "external_id": "pricesmart-tt-chaguanas",
        "name": "PriceSmart Chaguanas",
        "store_type": "supermarket",
        "address": {
            "road": "Narsaloo Ramaya Marg Road",
            "village": "Lendore",
            "city": "Chaguanas",
            "postcode": "500125",
            "country": "Trinidad and Tobago",
        },
        "latitude": 10.5285756,
        "longitude": -61.4077152,
        "source_notes": "Seeded manually from public OSM/Nominatim result for PriceSmart, Chaguanas.",
    },
    {
        "retailer": "PriceSmart",
        "retailer_website": "https://www.pricesmart.com/site/tt/en",
        "external_id": "pricesmart-tt-port-of-spain",
        "name": "PriceSmart Port of Spain",
        "store_type": "supermarket",
        "address": {
            "road": "MovieTowne Boulevard",
            "commercial": "MovieTowne",
            "suburb": "Woodbrook",
            "city": "Port of Spain",
            "postcode": "170312",
            "country": "Trinidad and Tobago",
        },
        "latitude": 10.6581936,
        "longitude": -61.5321568,
        "source_notes": "Seeded manually from public OSM/Nominatim result for PriceSmart, Port of Spain.",
    },
    {
        "retailer": "PriceSmart",
        "retailer_website": "https://www.pricesmart.com/site/tt/en",
        "external_id": "pricesmart-tt-mausica",
        "name": "PriceSmart Mausica",
        "store_type": "supermarket",
        "address": {
            "road": "Mausica Road",
            "quarter": "Maloney",
            "town": "Piarco",
            "state": "Tunapuna-Piarco",
            "postcode": "351443",
            "country": "Trinidad and Tobago",
        },
        "latitude": 10.6157639,
        "longitude": -61.3083781,
        "source_notes": "Seeded manually from public OSM/Nominatim result for PriceSmart, Mausica/Piarco.",
    },
    {
        "retailer": "PriceSmart",
        "retailer_website": "https://www.pricesmart.com/site/tt/en",
        "external_id": "pricesmart-tt-debe",
        "name": "PriceSmart Debe",
        "store_type": "supermarket",
        "address": {
            "road": "Pemberton Street",
            "village": "Rambert Village",
            "state": "Penal-Debe",
            "postcode": "651404",
            "country": "Trinidad and Tobago",
        },
        "latitude": 10.2487062,
        "longitude": -61.4850812,
        "source_notes": "Seeded manually from public OSM/Nominatim result for PriceSmart, Penal-Debe.",
    },
]


def get_or_create_retailer(session, name: str, website_url: str | None) -> Retailer:
    retailer = session.scalar(select(Retailer).where(Retailer.name == name))
    if retailer:
        if website_url and not retailer.website_url:
            retailer.website_url = website_url
        return retailer
    retailer = Retailer(
        name=name,
        website_url=website_url,
        integration_type="manual",
        loyalty_program_supported=True,
    )
    session.add(retailer)
    session.flush()
    return retailer


def seed() -> None:
    timestamp = now_utc()
    inserted = 0
    updated = 0

    with SessionLocal() as session:
        for item in MANUAL_STORES:
            retailer = get_or_create_retailer(session, item["retailer"], item["retailer_website"])
            store = session.scalar(
                select(Store).where(
                    Store.external_source == "manual",
                    Store.external_id == item["external_id"],
                )
            )
            payload = {
                "retailer_id": retailer.id,
                "name": item["name"],
                "store_type": item["store_type"],
                "address": item["address"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "contact_info": {"website": item["retailer_website"]},
                "service_capabilities": ["in_store"],
                "store_hours": None,
                "transit_accessibility": None,
                "external_source": "manual",
                "external_id": item["external_id"],
                "raw_tags": {"source_notes": item["source_notes"]},
                "is_active": True,
                "last_seen_at": timestamp,
                "source_updated_at": timestamp,
                "needs_review": False,
                "verified_at": timestamp,
            }
            if store:
                for key, value in payload.items():
                    setattr(store, key, value)
                updated += 1
            else:
                session.add(Store(**payload))
                inserted += 1

        session.commit()

    print({"inserted": inserted, "updated": updated})


if __name__ == "__main__":
    seed()
