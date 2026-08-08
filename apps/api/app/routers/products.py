from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db
from app.product_identity import normalize_product_text


router = APIRouter()


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


@router.get("/products/search")
def search_products(q: str, limit: int = 25, db: Session = Depends(get_db)) -> dict:
    tokens = [token for token in normalize_product_text(q).split() if token]
    if not tokens:
        return {"items": []}

    params = {"limit": limit}
    conditions = []
    for index, token in enumerate(tokens):
        key = f"token_{index}"
        params[key] = f"%{token}%"
        conditions.append(f"(cp.normalized_name ILIKE :{key} OR cp.selection_key ILIKE :{key})")

    sql = text(
        f"""
        with matches as (
            select
                cp.id,
                cp.canonical_name,
                cp.brand,
                cp.normalized_brand,
                cp.selection_key,
                cp.size_value,
                cp.size_unit,
                cp.package_quantity,
                pf.name as product_family_name,
                pf.selection_key as product_family_selection_key
            from canonical_products cp
            join product_families pf on pf.id = cp.product_family_id
            where {' and '.join(conditions)}
        )
        select
            matches.id,
            matches.canonical_name,
            matches.brand,
            matches.normalized_brand,
            matches.selection_key,
            matches.size_value,
            matches.size_unit,
            matches.package_quantity,
            matches.product_family_name,
            matches.product_family_selection_key,
            count(distinct pl.id) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as current_listing_count,
            count(distinct pl.id) filter (where pm.status = 'approved' and pm.confidence_level = 'high' and pl.stock_availability = 'in stock') as in_stock_listing_count,
            min(pl.price) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as current_min_price,
            max(pl.price_checked_at) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as latest_price_checked_at,
            count(distinct ppo.id) as historical_observation_count,
            max(ppo.observed_at) as latest_historical_observed_at
        from matches
        left join product_mappings pm on pm.canonical_product_id = matches.id
        left join product_listings pl on pl.id = pm.product_listing_id
        left join product_price_observations ppo on ppo.canonical_product_id = matches.id
        group by
            matches.id,
            matches.canonical_name,
            matches.brand,
            matches.normalized_brand,
            matches.selection_key,
            matches.size_value,
            matches.size_unit,
            matches.package_quantity,
            matches.product_family_name,
            matches.product_family_selection_key
        order by current_listing_count desc, historical_observation_count desc, matches.canonical_name
        limit :limit
        """
    )
    rows = db.execute(sql, params).mappings().all()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "canonical_name": row["canonical_name"],
                "brand": row["brand"],
                "normalized_brand": row["normalized_brand"],
                "selection_key": row["selection_key"],
                "size_value": row["size_value"],
                "size_unit": row["size_unit"],
                "package_quantity": row["package_quantity"],
                "product_family_name": row["product_family_name"],
                "product_family_selection_key": row["product_family_selection_key"],
                "current_listing_count": row["current_listing_count"],
                "in_stock_listing_count": row["in_stock_listing_count"],
                "current_min_price": _json_value(row["current_min_price"]),
                "latest_price_checked_at": row["latest_price_checked_at"],
                "historical_observation_count": row["historical_observation_count"],
                "latest_historical_observed_at": row["latest_historical_observed_at"],
            }
            for row in rows
        ]
    }
