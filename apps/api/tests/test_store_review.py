import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import (
    CanonicalProduct,
    ProductFamily,
    ProductPriceObservation,
    Retailer,
    Store,
    StoreAlias,
    StoreCandidate,
    StoreCandidateReview,
    now_utc,
)
from app.schemas.store_review import CandidateResolutionRequest, CreateStoreFromCandidateRequest
from app.services.store_review import (
    create_store_from_candidate,
    link_candidate_to_existing_store,
    mark_candidate_retailer_only,
    reject_candidate,
)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def review_fixture(db_session: Session):
    suffix = uuid.uuid4().hex[:10]
    retailer = Retailer(name=f"Review Test Retailer {suffix}", integration_type="test", loyalty_program_supported=False)
    db_session.add(retailer)
    db_session.flush()

    store = Store(
        retailer_id=retailer.id,
        name=f"Review Test Store {suffix}",
        store_type="supermarket",
        address={"text": "Test Address"},
        latitude=10.5,
        longitude=-61.4,
        contact_info=None,
        service_capabilities=[],
        store_hours=None,
        transit_accessibility=None,
        external_source="pytest",
        external_id=suffix,
        raw_tags={},
        is_active=True,
        needs_review=False,
    )
    db_session.add(store)

    family = ProductFamily(name=f"Review Test Flour {suffix}", category="Groceries", common_aliases=[])
    db_session.add(family)
    db_session.flush()

    product = CanonicalProduct(
        product_family_id=family.id,
        canonical_name=f"Review Test Flour 2kg {suffix}",
        brand="Test Brand",
        is_store_brand=False,
        category="Groceries",
        tags=[],
        requirements_supported=[],
        is_perishable=False,
    )
    db_session.add(product)
    db_session.flush()

    candidate = StoreCandidate(
        source="tradeind",
        raw_store_name=f"Review Candidate Store {suffix}",
        normalized_name=f"review candidate store {suffix}",
        raw_area="Test Area",
        raw_region="Test Region",
        retailer_id=retailer.id,
        status="needs_review",
        confidence=0.77,
        observations_count=2,
        first_seen_at=now_utc(),
        last_seen_at=now_utc(),
        evidence={"test": True},
    )
    db_session.add(candidate)
    db_session.flush()

    for price in [Decimal("10.00"), Decimal("11.00")]:
        db_session.add(
            ProductPriceObservation(
                canonical_product_id=product.id,
                retailer_id=None,
                store_id=None,
                region_code="TT",
                price=price,
                currency="TTD",
                observed_at=now_utc(),
                source="tradeind_xlsx",
                source_url=f"https://example.test/{suffix}.xlsx",
                raw_region=candidate.raw_region,
                raw_area=candidate.raw_area,
                raw_store_name=candidate.raw_store_name,
                raw_item_name="FLOUR",
                match_confidence=0.1,
                raw_payload={"test": True},
            )
        )
    db_session.commit()
    return {"retailer": retailer, "store": store, "candidate": candidate, "product": product}


def test_link_candidate_to_existing_store_backfills_observations_and_creates_alias(db_session: Session, review_fixture):
    store = review_fixture["store"]
    candidate = review_fixture["candidate"]

    review = link_candidate_to_existing_store(
        db_session,
        candidate.id,
        CandidateResolutionRequest(store_id=store.id, notes="Confirmed by reviewer"),
    )

    db_session.refresh(candidate)
    observations = db_session.scalars(
        select(ProductPriceObservation).where(ProductPriceObservation.raw_store_name == candidate.raw_store_name)
    ).all()
    alias = db_session.scalar(select(StoreAlias).where(StoreAlias.raw_name == candidate.raw_store_name))

    assert candidate.status == "approved_existing_store"
    assert candidate.matched_store_id == store.id
    assert review.action == "approved_existing_store"
    assert review.observations_backfilled == 2
    assert alias is not None
    assert alias.store_id == store.id
    assert all(observation.store_id == store.id for observation in observations)
    assert all(observation.retailer_id == store.retailer_id for observation in observations)


def test_create_store_from_candidate_creates_verified_store_alias_and_backfills(db_session: Session, review_fixture):
    retailer = review_fixture["retailer"]
    candidate = review_fixture["candidate"]

    review = create_store_from_candidate(
        db_session,
        candidate.id,
        CreateStoreFromCandidateRequest(
            retailer_id=retailer.id,
            name="Newly Verified Store",
            latitude=10.123,
            longitude=-61.123,
            address={"text": "Verified Address"},
            notes="Verified manually",
        ),
    )

    db_session.refresh(candidate)
    created_store = db_session.get(Store, review.created_store_id)
    alias = db_session.scalar(select(StoreAlias).where(StoreAlias.raw_name == candidate.raw_store_name))

    assert candidate.status == "approved_created_store"
    assert created_store is not None
    assert created_store.name == "Newly Verified Store"
    assert created_store.verified_at is not None
    assert alias is not None
    assert alias.store_id == created_store.id
    assert review.observations_backfilled == 2


def test_retailer_only_and_reject_write_review_records(db_session: Session, review_fixture):
    candidate = review_fixture["candidate"]

    retailer_only_review = mark_candidate_retailer_only(
        db_session,
        candidate.id,
        CandidateResolutionRequest(notes="Branch cannot be safely identified"),
    )
    db_session.refresh(candidate)

    assert candidate.status == "approved_retailer_only"
    assert retailer_only_review.action == "approved_retailer_only"

    reject_review = reject_candidate(
        db_session,
        candidate.id,
        CandidateResolutionRequest(notes="Later rejected as noisy"),
    )
    db_session.refresh(candidate)

    assert candidate.status == "rejected"
    assert reject_review.action == "rejected"
    reviews = db_session.scalars(select(StoreCandidateReview).where(StoreCandidateReview.candidate_id == candidate.id)).all()
    assert len(reviews) == 2
