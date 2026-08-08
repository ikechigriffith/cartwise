import math
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models import ProductPriceObservation, Store, StoreAlias, StoreCandidate, StoreCandidateReview, now_utc
from app.schemas.store_review import CandidateResolutionRequest, CreateStoreFromCandidateRequest
from scripts.import_tradeind_price_data import normalize

TRADEIND_OBSERVATION_SOURCES = {"tradeind_xlsx", "tradeind_pdf_text"}

# Approximate area centroids used only to suggest candidate matches for human review.
# They are not written to trusted Store rows.
TT_AREA_CENTROIDS = {
    "arima": (10.6374, -61.2823),
    "arouca": (10.6286, -61.3334),
    "barataria": (10.6519, -61.4564),
    "chaguanas": (10.5168, -61.4114),
    "charlotteville": (11.3232, -60.5526),
    "couva": (10.4236, -61.4675),
    "cumana": (10.7833, -60.9833),
    "cunupia": (10.5472, -61.3736),
    "curepe": (10.6414, -61.4113),
    "debe": (10.2081, -61.4524),
    "diego martin": (10.7208, -61.5662),
    "fyzabad": (10.1782, -61.5486),
    "gasparillo": (10.3229, -61.4245),
    "marabella": (10.3065, -61.4469),
    "mayaro": (10.2901, -60.9948),
    "plymouth": (11.1852, -60.7798),
    "point fortin": (10.1741, -61.6841),
    "port of spain": (10.6667, -61.5167),
    "princes town": (10.2670, -61.3764),
    "rio claro": (10.3059, -61.1756),
    "san fernando": (10.2797, -61.4684),
    "san juan": (10.6521, -61.4491),
    "sangre grande": (10.5871, -61.1322),
    "scarborough": (11.1823, -60.7352),
    "siparia": (10.1453, -61.5074),
    "st james": (10.6757, -61.5331),
    "tobago": (11.2500, -60.6670),
    "toco": (10.8279, -60.9554),
    "trincity": (10.6279, -61.3561),
    "tunapuna": (10.6524, -61.3888),
}


def candidate_observation_filter(candidate: StoreCandidate):
    return and_(
        ProductPriceObservation.source.in_(TRADEIND_OBSERVATION_SOURCES),
        ProductPriceObservation.raw_store_name == candidate.raw_store_name,
        ProductPriceObservation.raw_area == candidate.raw_area,
        ProductPriceObservation.raw_region == candidate.raw_region,
    )


def store_candidate_filters(status: str | None = "needs_review", q: str | None = None):
    filters = []
    if status:
        filters.append(StoreCandidate.status == status)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                StoreCandidate.raw_store_name.ilike(pattern),
                StoreCandidate.normalized_name.ilike(pattern),
                StoreCandidate.raw_area.ilike(pattern),
                StoreCandidate.raw_region.ilike(pattern),
            )
        )
    return filters


def list_store_candidates(session: Session, status: str | None = "needs_review", q: str | None = None, limit: int = 100, offset: int = 0) -> list[StoreCandidate]:
    statement = select(StoreCandidate).order_by(StoreCandidate.observations_count.desc(), StoreCandidate.last_seen_at.desc())
    filters = store_candidate_filters(status, q)
    if filters:
        statement = statement.where(*filters)
    return list(session.scalars(statement.limit(limit).offset(offset)).all())


def count_store_candidates(session: Session, status: str | None = "needs_review", q: str | None = None) -> int:
    statement = select(func.count(StoreCandidate.id))
    filters = store_candidate_filters(status, q)
    if filters:
        statement = statement.where(*filters)
    return session.scalar(statement) or 0


def get_store_candidate(session: Session, candidate_id: uuid.UUID) -> StoreCandidate:
    candidate = session.get(StoreCandidate, candidate_id)
    if not candidate:
        raise ValueError("Store candidate not found")
    return candidate


def sample_candidate_observations(session: Session, candidate: StoreCandidate, limit: int = 20) -> list[ProductPriceObservation]:
    return list(
        session.scalars(
            select(ProductPriceObservation)
            .where(candidate_observation_filter(candidate))
            .order_by(ProductPriceObservation.observed_at.desc())
            .limit(limit)
        ).all()
    )


def create_alias_for_candidate(
    session: Session,
    candidate: StoreCandidate,
    store_id: uuid.UUID,
    reviewed_by: uuid.UUID | None,
    notes: str | None,
) -> StoreAlias:
    alias = session.scalar(
        select(StoreAlias).where(
            StoreAlias.source == candidate.source,
            StoreAlias.raw_name == candidate.raw_store_name,
            StoreAlias.raw_area == candidate.raw_area,
            StoreAlias.raw_region == candidate.raw_region,
        )
    )
    now = now_utc()
    if not alias:
        alias = StoreAlias(
            store_id=store_id,
            source=candidate.source,
            raw_name=candidate.raw_store_name,
            normalized_name=normalize(candidate.raw_store_name),
            raw_area=candidate.raw_area,
            raw_region=candidate.raw_region,
            created_at=now,
            updated_at=now,
        )
        session.add(alias)
    alias.store_id = store_id
    alias.confidence = candidate.confidence
    alias.approved_by = reviewed_by
    alias.approved_at = now
    alias.notes = notes
    alias.updated_at = now
    return alias


def backfill_candidate_observations(session: Session, candidate: StoreCandidate, store_id: uuid.UUID) -> int:
    store = session.get(Store, store_id)
    if not store:
        raise ValueError("Store not found")
    result = session.execute(
        update(ProductPriceObservation)
        .where(candidate_observation_filter(candidate))
        .values(store_id=store.id, retailer_id=store.retailer_id, updated_at=now_utc())
    )
    return result.rowcount or 0


def link_candidate_to_existing_store(session: Session, candidate_id: uuid.UUID, request: CandidateResolutionRequest) -> StoreCandidateReview:
    if not request.store_id:
        raise ValueError("store_id is required")
    candidate = get_store_candidate(session, candidate_id)
    if not session.get(Store, request.store_id):
        raise ValueError("Store not found")
    backfilled = backfill_candidate_observations(session, candidate, request.store_id)
    create_alias_for_candidate(session, candidate, request.store_id, request.reviewed_by, request.notes)
    now = now_utc()
    candidate.matched_store_id = request.store_id
    candidate.status = "approved_existing_store"
    candidate.notes = request.notes
    candidate.updated_at = now
    review = StoreCandidateReview(
        candidate_id=candidate.id,
        action="approved_existing_store",
        existing_store_id=request.store_id,
        reviewed_by=request.reviewed_by,
        reviewed_at=now,
        fields_changed=request.fields_changed,
        observations_backfilled=backfilled,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def create_store_from_candidate(session: Session, candidate_id: uuid.UUID, request: CreateStoreFromCandidateRequest) -> StoreCandidateReview:
    candidate = get_store_candidate(session, candidate_id)
    now = now_utc()
    store = Store(
        retailer_id=request.retailer_id,
        name=request.name,
        store_type=request.store_type,
        address=request.address,
        latitude=request.latitude,
        longitude=request.longitude,
        contact_info=None,
        service_capabilities=[],
        store_hours=None,
        transit_accessibility=None,
        external_source="tradeind_review",
        external_id=str(candidate.id),
        raw_tags={"store_candidate_id": str(candidate.id), "raw_store_name": candidate.raw_store_name},
        is_active=True,
        last_seen_at=candidate.last_seen_at,
        source_updated_at=None,
        needs_review=False,
        verified_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(store)
    session.flush()
    backfilled = backfill_candidate_observations(session, candidate, store.id)
    create_alias_for_candidate(session, candidate, store.id, request.reviewed_by, request.notes)
    candidate.matched_store_id = store.id
    candidate.status = "approved_created_store"
    candidate.notes = request.notes
    candidate.updated_at = now
    review = StoreCandidateReview(
        candidate_id=candidate.id,
        action="approved_created_store",
        created_store_id=store.id,
        reviewed_by=request.reviewed_by,
        reviewed_at=now,
        fields_changed={"created_store": {"name": store.name, "latitude": store.latitude, "longitude": store.longitude}},
        observations_backfilled=backfilled,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def mark_candidate_retailer_only(session: Session, candidate_id: uuid.UUID, request: CandidateResolutionRequest) -> StoreCandidateReview:
    candidate = get_store_candidate(session, candidate_id)
    now = now_utc()
    candidate.status = "approved_retailer_only"
    candidate.notes = request.notes
    candidate.updated_at = now
    review = StoreCandidateReview(
        candidate_id=candidate.id,
        action="approved_retailer_only",
        reviewed_by=request.reviewed_by,
        reviewed_at=now,
        fields_changed=request.fields_changed,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def reject_candidate(session: Session, candidate_id: uuid.UUID, request: CandidateResolutionRequest) -> StoreCandidateReview:
    candidate = get_store_candidate(session, candidate_id)
    now = now_utc()
    candidate.status = "rejected"
    candidate.notes = request.notes
    candidate.updated_at = now
    review = StoreCandidateReview(
        candidate_id=candidate.id,
        action="rejected",
        reviewed_by=request.reviewed_by,
        reviewed_at=now,
        fields_changed=request.fields_changed,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def candidate_counts_by_status(session: Session) -> dict[str, int]:
    rows = session.execute(select(StoreCandidate.status, func.count(StoreCandidate.id)).group_by(StoreCandidate.status)).all()
    return {status: count for status, count in rows}


def area_centroid(raw_area: str | None) -> tuple[float, float] | None:
    if not raw_area:
        return None
    normalized = normalize(raw_area).replace("'", "")
    for part in re_split_area(normalized):
        if part in TT_AREA_CENTROIDS:
            return TT_AREA_CENTROIDS[part]
    for key, centroid in TT_AREA_CENTROIDS.items():
        if key in normalized:
            return centroid
    return None


def re_split_area(value: str) -> list[str]:
    return [part.strip() for part in value.replace("montrose", "cunupia").replace("/", " ").split() if part.strip()]


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def store_text(store: Store) -> str:
    address = store.address or {}
    address_text = " ".join(str(value) for value in address.values() if value)
    retailer_name = store.retailer.name if store.retailer else ""
    return normalize(f"{retailer_name} {store.name} {address_text}")


def suggest_existing_stores(session: Session, candidate: StoreCandidate, limit: int = 10) -> list[dict[str, Any]]:
    centroid = area_centroid(candidate.raw_area)
    stores = session.scalars(select(Store).where(Store.is_active.is_(True))).all()
    candidate_name = normalize(candidate.raw_store_name)
    candidate_area = normalize(candidate.raw_area)
    suggestions: list[dict[str, Any]] = []

    for store in stores:
        text = store_text(store)
        score = 0.0
        reasons: list[str] = []

        if candidate.retailer_id and store.retailer_id == candidate.retailer_id:
            score += 0.45
            reasons.append("same retailer")
        elif candidate_name and normalize(store.retailer.name if store.retailer else "") in candidate_name:
            score += 0.25
            reasons.append("retailer name appears in source label")

        if candidate_area and candidate_area in text:
            score += 0.30
            reasons.append("area appears in store name/address")

        name_tokens = set(candidate_name.split())
        text_tokens = set(text.split())
        overlap = len(name_tokens & text_tokens)
        if overlap:
            score += min(0.20, overlap * 0.04)
            reasons.append("name tokens overlap")

        distance_km = None
        if centroid and store.latitude is not None and store.longitude is not None:
            distance_km = haversine_km(centroid, (store.latitude, store.longitude))
            if distance_km <= 3:
                score += 0.35
                reasons.append("within 3km of source area centroid")
            elif distance_km <= 8:
                score += 0.20
                reasons.append("within 8km of source area centroid")
            elif distance_km <= 15:
                score += 0.10
                reasons.append("within 15km of source area centroid")

        if score <= 0:
            continue
        suggestions.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "retailer_name": store.retailer.name if store.retailer else None,
                "address": store.address,
                "latitude": store.latitude,
                "longitude": store.longitude,
                "score": round(score, 3),
                "distance_km": round(distance_km, 2) if distance_km is not None else None,
                "reasons": reasons,
            }
        )

    return sorted(suggestions, key=lambda item: (item["score"], -(item["distance_km"] or 9999)), reverse=True)[:limit]
