from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Retailer, RetailerDataSource


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


SOURCES = [
    {
        "retailer": "PriceSmart",
        "source_url": "https://www.pricesmart.com/site/tt/en",
        "source_type": "website",
        "has_product_catalog": True,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "candidate_strong",
        "confidence": "high",
        "notes": "Strong candidate. Site has online shopping/catalog behavior and likely structured APIs behind the frontend. Needs product/price proof-of-concept.",
    },
    {
        "retailer": "Massy Stores",
        "source_url": "https://massystorestt.com/",
        "source_type": "website",
        "has_product_catalog": None,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "candidate_likely",
        "confidence": "medium",
        "notes": "Likely candidate. Website is live and has shopping/product signals. Needs deeper verification for visible prices and store-specific availability.",
    },
    {
        "retailer": "Xtra Foods",
        "source_url": "https://xtrafoods.com/",
        "source_type": "website",
        "has_product_catalog": None,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "needs_verification",
        "confidence": "unknown",
        "notes": "Major retailer. Initial request timed out; retry and verify online catalog/pricing.",
    },
    {
        "retailer": "JTA Supermarkets",
        "source_url": "https://jtasupermarkets.com/",
        "source_type": "website",
        "has_product_catalog": None,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "needs_verification",
        "confidence": "unknown",
        "notes": "Website found. Initial scan did not clearly show online product pricing.",
    },
    {
        "retailer": "Persad's D' Food King",
        "source_url": "https://persadsdfoodking.com/",
        "source_type": "website",
        "has_product_catalog": None,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "needs_verification",
        "confidence": "unknown",
        "notes": "Website found. Needs verification for product catalog and prices.",
    },
    {
        "retailer": "SuperPharm",
        "source_url": "https://superpharmtt.com/",
        "source_type": "website",
        "has_product_catalog": None,
        "has_prices": None,
        "has_stock": None,
        "requires_login": None,
        "scrape_status": "needs_verification",
        "confidence": "unknown",
        "notes": "Retail/pharmacy source that may cover household and grocery-adjacent products. Needs verification.",
    },
]


def get_or_create_retailer(session, name: str) -> Retailer:
    retailer = session.scalar(select(Retailer).where(Retailer.name == name))
    if retailer:
        return retailer
    retailer = Retailer(name=name, integration_type="manual", loyalty_program_supported=False)
    session.add(retailer)
    session.flush()
    return retailer


def seed() -> None:
    timestamp = now_utc()
    inserted = 0
    updated = 0

    with SessionLocal() as session:
        for item in SOURCES:
            retailer = get_or_create_retailer(session, item["retailer"])
            if not retailer.website_url:
                retailer.website_url = item["source_url"]

            source = session.scalar(
                select(RetailerDataSource).where(
                    RetailerDataSource.retailer_id == retailer.id,
                    RetailerDataSource.source_url == item["source_url"],
                )
            )
            payload = {
                "retailer_id": retailer.id,
                "source_url": item["source_url"],
                "source_type": item["source_type"],
                "has_product_catalog": item["has_product_catalog"],
                "has_prices": item["has_prices"],
                "has_stock": item["has_stock"],
                "requires_login": item["requires_login"],
                "scrape_status": item["scrape_status"],
                "confidence": item["confidence"],
                "last_checked_at": timestamp,
                "notes": item["notes"],
            }
            if source:
                for key, value in payload.items():
                    setattr(source, key, value)
                updated += 1
            else:
                session.add(RetailerDataSource(**payload))
                inserted += 1

        session.commit()

    print({"inserted": inserted, "updated": updated})


if __name__ == "__main__":
    seed()
