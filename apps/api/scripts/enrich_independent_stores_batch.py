import json
from sqlalchemy import select, text
from app.db import SessionLocal
from app.models import Store, Retailer, now_utc

ADDITIONAL_ENRICHED_STORES = [
    {
        "pattern": "%Price Club%",
        "contact": {
            "phone": "+1 868-665-7777",
            "facebook": "https://www.facebook.com/ThePriceClubSupermarket",
            "address": "Centre Pointe Mall, Ramsaran Street, Chaguanas"
        }
    },
    {
        "pattern": "%West Bees%",
        "contact": {
            "phone": "+1 868-632-8150",
            "whatsapp": "+1 868-377-2119",
            "facebook": "https://www.facebook.com/westbeessupermarket",
            "address": "West Bees Shopping Plaza, 7-11 Diego Martin Main Road, Diego Martin"
        }
    },
    {
        "pattern": "%MS Food City%",
        "contact": {
            "phone": "+1 868-393-2800",
            "facebook": "https://www.facebook.com/M.S.FoodcitySupermarketLTD",
            "address": "1110-1112 S.S. Erin Main Road, Debe, Trinidad"
        }
    },
    {
        "pattern": "%Anand%",
        "contact": {
            "phone": "+1 868-331-2951",
            "facebook": "https://www.facebook.com/AnandLowPriceSupermarket"
        }
    },
    {
        "pattern": "%Persad%",
        "contact": {
            "phone": "+1 868-654-1240",
            "facebook": "https://www.facebook.com/persadsdfoodking"
        }
    },
    {
        "pattern": "%Disko%",
        "contact": {
            "phone": "+1 868-663-8888",
            "facebook": "https://www.facebook.com/diskomarttt"
        }
    },
    {
        "pattern": "%Toolsie%",
        "contact": {
            "phone": "+1 868-636-4444",
            "address": "Grant Street, Couva"
        }
    },
    {
        "pattern": "%Coss Cutter%",
        "contact": {
            "phone": "+1 868-668-3721",
            "facebook": "https://www.facebook.com/costcutterssupermarket",
            "address": "George Street, Sangre Grande"
        }
    },
]


def deep_enrich_batch() -> int:
    updated = 0
    now = now_utc()
    with SessionLocal() as session:
        for item in ADDITIONAL_ENRICHED_STORES:
            pattern = item["pattern"]
            new_info = item["contact"]
            stores = session.scalars(select(Store).where(Store.name.ilike(pattern))).all()
            for s in stores:
                existing = s.contact_info or {}
                merged = {**existing, **new_info}
                if merged != existing:
                    s.contact_info = merged
                    s.updated_at = now
                    updated += 1
            retailers = session.scalars(select(Retailer).where(Retailer.name.ilike(pattern))).all()
            for r in retailers:
                existing = r.contact_info or {}
                merged = {**existing, **new_info}
                if merged != existing:
                    r.contact_info = merged
                    r.updated_at = now

        session.commit()
    return updated


if __name__ == "__main__":
    count = deep_enrich_batch()
    print(f"Deep store enrichment completed. Updated {count} stores with web-verified details.")
