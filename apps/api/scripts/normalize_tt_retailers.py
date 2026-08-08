import json

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import Retailer, Store

# Conservative aliases only. Accuracy is more important than aggressive grouping.
ALIASES = {
    "Jta": "JTA Supermarkets",
    "JTA Supermarket": "JTA Supermarkets",
    "JTA Supermakets": "JTA Supermarkets",
    "Massy": "Massy Stores",
    "Tru-Valu": "Tru Valu",
    "Persads": "Persad's D' Food King",
    "Persad's": "Persad's D' Food King",
    "Np": "National Petroleum",
}


def get_or_create_retailer(session, canonical_name: str) -> Retailer:
    retailer = session.scalar(select(Retailer).where(Retailer.name == canonical_name))
    if retailer:
        return retailer
    retailer = Retailer(name=canonical_name, integration_type="osm", loyalty_program_supported=False)
    session.add(retailer)
    session.flush()
    return retailer


def normalize() -> None:
    changes: list[dict[str, object]] = []
    with SessionLocal() as session:
        for alias, canonical in ALIASES.items():
            alias_retailer = session.scalar(select(Retailer).where(Retailer.name == alias))
            if not alias_retailer:
                continue

            canonical_retailer = get_or_create_retailer(session, canonical)
            store_count = session.scalar(select(func.count(Store.id)).where(Store.retailer_id == alias_retailer.id)) or 0

            session.query(Store).filter(Store.retailer_id == alias_retailer.id).update(
                {Store.retailer_id: canonical_retailer.id}, synchronize_session=False
            )
            session.execute(delete(Retailer).where(Retailer.id == alias_retailer.id))
            changes.append({"from": alias, "to": canonical, "stores": store_count})

        session.commit()

    print(json.dumps({"normalized": changes}, indent=2))


if __name__ == "__main__":
    normalize()
