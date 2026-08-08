from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import ProductSelectionReview
from app.schemas.product_selection_review import ProductSelectionApprovalRequest
from app.services.product_selection_review import (
    approve_product_selection_group,
    count_product_selection_groups,
    list_product_selection_groups,
    product_selection_group_detail,
)

router = APIRouter(prefix="/admin/product-selection-reviews", dependencies=[Depends(require_admin)])


def serialize_review(review: ProductSelectionReview) -> dict:
    return {
        "id": review.id,
        "selection_key": review.selection_key,
        "action": review.action,
        "product_family_id": review.product_family_id,
        "reviewed_by": review.reviewed_by,
        "reviewed_at": review.reviewed_at,
        "canonical_products_updated": review.canonical_products_updated,
        "fields_changed": review.fields_changed,
        "notes": review.notes,
    }


@router.get("")
def admin_product_selection_reviews(q: str | None = None, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)) -> dict:
    return {
        "total": count_product_selection_groups(db, q=q),
        "limit": limit,
        "offset": offset,
        "items": list_product_selection_groups(db, q=q, limit=limit, offset=offset),
    }


@router.get("/{selection_key}")
def admin_product_selection_review_detail(selection_key: str, db: Session = Depends(get_db)) -> dict:
    try:
        return product_selection_group_detail(db, selection_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{selection_key}/approve-family")
def admin_approve_product_selection_group(selection_key: str, request: ProductSelectionApprovalRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return {"review": serialize_review(approve_product_selection_group(db, selection_key, request))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
