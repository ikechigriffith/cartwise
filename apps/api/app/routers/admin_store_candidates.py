import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import StoreCandidate, StoreCandidateReview
from app.schemas.store_review import CandidateResolutionRequest, CreateStoreFromCandidateRequest
from app.services.store_review import (
    candidate_counts_by_status,
    count_store_candidates,
    create_store_from_candidate,
    get_store_candidate,
    link_candidate_to_existing_store,
    list_store_candidates,
    mark_candidate_retailer_only,
    reject_candidate,
    sample_candidate_observations,
    suggest_existing_stores,
)

router = APIRouter(prefix="/admin/store-candidates", dependencies=[Depends(require_admin)])


def serialize_candidate(candidate: StoreCandidate) -> dict:
    return {
        "id": candidate.id,
        "source": candidate.source,
        "raw_store_name": candidate.raw_store_name,
        "normalized_name": candidate.normalized_name,
        "raw_area": candidate.raw_area,
        "raw_region": candidate.raw_region,
        "retailer_id": candidate.retailer_id,
        "retailer_name": candidate.retailer.name if candidate.retailer else None,
        "matched_store_id": candidate.matched_store_id,
        "matched_store_name": candidate.matched_store.name if candidate.matched_store else None,
        "status": candidate.status,
        "confidence": candidate.confidence,
        "observations_count": candidate.observations_count,
        "first_seen_at": candidate.first_seen_at,
        "last_seen_at": candidate.last_seen_at,
        "evidence": candidate.evidence,
        "notes": candidate.notes,
    }


def serialize_review(review: StoreCandidateReview) -> dict:
    return {
        "id": review.id,
        "candidate_id": review.candidate_id,
        "action": review.action,
        "existing_store_id": review.existing_store_id,
        "created_store_id": review.created_store_id,
        "reviewed_by": review.reviewed_by,
        "reviewed_at": review.reviewed_at,
        "fields_changed": review.fields_changed,
        "observations_backfilled": review.observations_backfilled,
        "notes": review.notes,
    }


@router.get("")
def admin_store_candidates(
    status: str | None = "needs_review",
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    resolved_status = None if status == "all" else status
    return {
        "counts_by_status": candidate_counts_by_status(db),
        "total": count_store_candidates(db, status=resolved_status, q=q),
        "limit": limit,
        "offset": offset,
        "items": [serialize_candidate(candidate) for candidate in list_store_candidates(db, status=resolved_status, q=q, limit=limit, offset=offset)],
    }


@router.get("/{candidate_id}")
def admin_store_candidate_detail(candidate_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    try:
        candidate = get_store_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    samples = sample_candidate_observations(db, candidate)
    return {
        "candidate": serialize_candidate(candidate),
        "suggested_store_matches": suggest_existing_stores(db, candidate),
        "sample_observations": [
            {
                "id": observation.id,
                "observed_at": observation.observed_at,
                "price": float(observation.price) if isinstance(observation.price, Decimal) else observation.price,
                "raw_item_name": observation.raw_item_name,
                "raw_store_name": observation.raw_store_name,
                "raw_area": observation.raw_area,
                "raw_region": observation.raw_region,
                "source": observation.source,
                "source_url": observation.source_url,
            }
            for observation in samples
        ],
    }


@router.post("/{candidate_id}/link-existing-store")
def admin_link_existing_store(candidate_id: uuid.UUID, request: CandidateResolutionRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return {"review": serialize_review(link_candidate_to_existing_store(db, candidate_id, request))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/create-store")
def admin_create_store(candidate_id: uuid.UUID, request: CreateStoreFromCandidateRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return {"review": serialize_review(create_store_from_candidate(db, candidate_id, request))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/retailer-only")
def admin_retailer_only(candidate_id: uuid.UUID, request: CandidateResolutionRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return {"review": serialize_review(mark_candidate_retailer_only(db, candidate_id, request))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/reject")
def admin_reject_candidate(candidate_id: uuid.UUID, request: CandidateResolutionRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return {"review": serialize_review(reject_candidate(db, candidate_id, request))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
