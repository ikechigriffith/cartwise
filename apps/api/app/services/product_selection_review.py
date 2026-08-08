from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import CanonicalProduct, ProductFamily, ProductSelectionReview, now_utc
from app.schemas.product_selection_review import ProductSelectionApprovalRequest


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def list_product_selection_groups(session: Session, q: str | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    filters = ["cp.selection_key is not null", "cp.selection_key <> ''"]
    if q:
        params["q"] = f"%{q}%"
        filters.append("(cp.selection_key ilike :q or cp.normalized_name ilike :q)")
    sql = text(
        f"""
        select
            cp.selection_key,
            count(distinct cp.id) as canonical_product_count,
            count(distinct cp.product_family_id) as product_family_count,
            count(distinct pl.id) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as current_listing_count,
            count(distinct cp.id) filter (where pl.id is not null and pm.status = 'approved' and pm.confidence_level = 'high') as current_listing_product_count,
            count(distinct ppo.id) as historical_observation_count,
            count(distinct cp.id) filter (where ppo.id is not null) as historical_product_count,
            max(greatest(coalesce(pl.price_checked_at, 'epoch'::timestamptz), coalesce(ppo.observed_at, 'epoch'::timestamptz))) as latest_seen_at,
            max(psr.reviewed_at) as last_reviewed_at
        from canonical_products cp
        left join product_mappings pm on pm.canonical_product_id = cp.id
        left join product_listings pl on pl.id = pm.product_listing_id
        left join product_price_observations ppo on ppo.canonical_product_id = cp.id
        left join product_selection_reviews psr on psr.selection_key = cp.selection_key
        where {' and '.join(filters)}
        group by cp.selection_key
        having count(distinct cp.product_family_id) > 1
        order by historical_observation_count desc, current_listing_count desc, canonical_product_count desc, cp.selection_key
        limit :limit offset :offset
        """
    )
    return [dict(row) for row in session.execute(sql, params).mappings().all()]


def count_product_selection_groups(session: Session, q: str | None = None) -> int:
    params: dict[str, Any] = {}
    filters = ["selection_key is not null", "selection_key <> ''"]
    if q:
        params["q"] = f"%{q}%"
        filters.append("(selection_key ilike :q or normalized_name ilike :q)")
    sql = text(
        f"""
        select count(*) from (
            select selection_key
            from canonical_products
            where {' and '.join(filters)}
            group by selection_key
            having count(distinct product_family_id) > 1
        ) groups
        """
    )
    return session.execute(sql, params).scalar_one()


def product_selection_group_detail(session: Session, selection_key: str) -> dict[str, Any]:
    products = session.execute(
        text(
            """
            select
                cp.id,
                cp.canonical_name,
                cp.brand,
                cp.normalized_brand,
                cp.selection_key,
                cp.size_value,
                cp.size_unit,
                cp.package_quantity,
                pf.id as product_family_id,
                pf.name as product_family_name,
                count(distinct pl.id) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as current_listing_count,
                count(distinct pl.id) filter (where pm.status = 'approved' and pm.confidence_level = 'high' and pl.stock_availability = 'in stock') as in_stock_listing_count,
                min(pl.price) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as current_min_price,
                max(pl.price_checked_at) filter (where pm.status = 'approved' and pm.confidence_level = 'high') as latest_price_checked_at,
                count(distinct ppo.id) as historical_observation_count,
                max(ppo.observed_at) as latest_historical_observed_at
            from canonical_products cp
            join product_families pf on pf.id = cp.product_family_id
            left join product_mappings pm on pm.canonical_product_id = cp.id
            left join product_listings pl on pl.id = pm.product_listing_id
            left join product_price_observations ppo on ppo.canonical_product_id = cp.id
            where cp.selection_key = :selection_key
            group by cp.id, pf.id, pf.name
            order by current_listing_count desc, historical_observation_count desc, cp.canonical_name
            """
        ),
        {"selection_key": selection_key},
    ).mappings().all()
    if not products:
        raise ValueError("Product selection group not found")

    listings = session.execute(
        text(
            """
            select
                pl.id,
                pl.raw_name,
                pl.raw_brand,
                pl.price,
                pl.currency,
                pl.stock_availability,
                pl.price_checked_at,
                s.name as store_name,
                r.name as retailer_name,
                cp.id as canonical_product_id,
                cp.canonical_name
            from product_listings pl
            join product_mappings pm on pm.product_listing_id = pl.id
            join canonical_products cp on cp.id = pm.canonical_product_id
            join stores s on s.id = pl.store_id
            join retailers r on r.id = s.retailer_id
            where cp.selection_key = :selection_key and pm.status = 'approved' and pm.confidence_level = 'high'
            order by pl.price_checked_at desc nulls last, pl.raw_name
            limit 30
            """
        ),
        {"selection_key": selection_key},
    ).mappings().all()

    observations = session.execute(
        text(
            """
            select
                ppo.id,
                ppo.raw_item_name,
                ppo.price,
                ppo.currency,
                ppo.observed_at,
                ppo.raw_store_name,
                ppo.raw_area,
                ppo.raw_region,
                ppo.source,
                cp.id as canonical_product_id,
                cp.canonical_name
            from product_price_observations ppo
            join canonical_products cp on cp.id = ppo.canonical_product_id
            where cp.selection_key = :selection_key
            order by ppo.observed_at desc, ppo.raw_item_name
            limit 30
            """
        ),
        {"selection_key": selection_key},
    ).mappings().all()

    reviews = session.execute(
        text(
            """
            select id, action, product_family_id, reviewed_by, reviewed_at, canonical_products_updated, fields_changed, notes
            from product_selection_reviews
            where selection_key = :selection_key
            order by reviewed_at desc
            limit 10
            """
        ),
        {"selection_key": selection_key},
    ).mappings().all()

    return {
        "selection_key": selection_key,
        "canonical_products": [{key: _json_value(value) for key, value in dict(row).items()} for row in products],
        "current_listings": [{key: _json_value(value) for key, value in dict(row).items()} for row in listings],
        "historical_observations": [{key: _json_value(value) for key, value in dict(row).items()} for row in observations],
        "reviews": [dict(row) for row in reviews],
    }


def approve_product_selection_group(session: Session, selection_key: str, request: ProductSelectionApprovalRequest) -> ProductSelectionReview:
    target_family = session.get(ProductFamily, request.product_family_id)
    if not target_family:
        raise ValueError("Product family not found")

    products = list(session.scalars(text("select id from canonical_products where selection_key = :selection_key"), {"selection_key": selection_key}).all())
    if not products:
        raise ValueError("Product selection group not found")

    canonical_products = list(session.query(CanonicalProduct).filter(CanonicalProduct.selection_key == selection_key).all())
    existing_family_ids = {product.product_family_id for product in canonical_products}
    if target_family.id not in existing_family_ids:
        raise ValueError("Target product family must belong to this selection group")

    now = now_utc()
    previous_family_ids = sorted(str(value) for value in existing_family_ids)
    updated = 0
    for product in canonical_products:
        if product.product_family_id != target_family.id:
            product.product_family_id = target_family.id
            product.updated_at = now
            updated += 1

    target_family.selection_key = target_family.selection_key or selection_key
    target_family.updated_at = now
    fields_changed = {
        "previous_product_family_ids": previous_family_ids,
        "target_product_family_id": str(target_family.id),
        **(request.fields_changed or {}),
    }
    review = ProductSelectionReview(
        selection_key=selection_key,
        action="approved_family_consolidation",
        product_family_id=target_family.id,
        reviewed_by=request.reviewed_by,
        reviewed_at=now,
        canonical_products_updated=updated,
        fields_changed=fields_changed,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review
