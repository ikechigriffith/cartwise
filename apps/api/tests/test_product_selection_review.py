import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db import engine
from app.models import (
    CanonicalProduct,
    ProductFamily,
    ProductListing,
    ProductMapping,
    ProductPriceObservation,
    ProductSelectionReview,
    Retailer,
    Store,
    now_utc,
)
from app.product_identity import build_product_identity
from app.schemas.product_selection_review import ProductSelectionApprovalRequest
from app.services.product_selection_review import (
    approve_product_selection_group,
    list_product_selection_groups,
    product_selection_group_detail,
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
def product_review_fixture(db_session: Session):
    suffix = uuid.uuid4().hex[:10]
    first_identity = build_product_identity(f"Review Cereal {suffix} 500g", brand="Review Brand")
    second_identity = build_product_identity(f"Review Cereal {suffix} 1kg", brand="Review Brand")
    selection_key = first_identity.selection_key

    retailer = Retailer(name=f"Review Product Retailer {suffix}", integration_type="test", loyalty_program_supported=False)
    db_session.add(retailer)
    db_session.flush()
    store = Store(
        retailer_id=retailer.id,
        name=f"Review Product Store {suffix}",
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

    family_a = ProductFamily(
        name=f"Review Cereal A {suffix}",
        normalized_name=f"review cereal a {suffix}",
        selection_key=selection_key,
        category="Groceries",
        common_aliases=[],
    )
    family_b = ProductFamily(
        name=f"Review Cereal B {suffix}",
        normalized_name=f"review cereal b {suffix}",
        selection_key=selection_key,
        category="Groceries",
        common_aliases=[],
    )
    db_session.add_all([family_a, family_b])
    db_session.flush()

    product_a = CanonicalProduct(
        product_family_id=family_a.id,
        canonical_name=first_identity.clean_name,
        normalized_name=first_identity.normalized_name,
        selection_key=selection_key,
        brand="Review Brand",
        normalized_brand=first_identity.normalized_brand,
        is_store_brand=False,
        category="Groceries",
        size_value=first_identity.parsed_size_value,
        size_unit=first_identity.parsed_size_unit,
        tags=[],
        requirements_supported=[],
        is_perishable=False,
    )
    product_b = CanonicalProduct(
        product_family_id=family_b.id,
        canonical_name=second_identity.clean_name,
        normalized_name=second_identity.normalized_name,
        selection_key=selection_key,
        brand="Review Brand",
        normalized_brand=second_identity.normalized_brand,
        is_store_brand=False,
        category="Groceries",
        size_value=second_identity.parsed_size_value,
        size_unit=second_identity.parsed_size_unit,
        tags=[],
        requirements_supported=[],
        is_perishable=False,
    )
    db_session.add_all([product_a, product_b])
    db_session.flush()

    listing = ProductListing(
        store_id=store.id,
        retailer_product_id=f"review-{suffix}",
        raw_name=first_identity.clean_name,
        normalized_name=first_identity.normalized_name,
        selection_key=selection_key,
        raw_brand="Review Brand",
        normalized_brand=first_identity.normalized_brand,
        price=Decimal("12.50"),
        currency="TTD",
        stock_availability="in stock",
        source="pytest",
        price_checked_at=now_utc(),
        stock_checked_at=now_utc(),
    )
    db_session.add(listing)
    db_session.flush()
    db_session.add(
        ProductMapping(
            product_listing_id=listing.id,
            canonical_product_id=product_a.id,
            confidence=1.0,
            confidence_level="high",
            mapping_method="pytest",
            status="approved",
        )
    )
    db_session.add(
        ProductPriceObservation(
            canonical_product_id=product_b.id,
            retailer_id=retailer.id,
            store_id=store.id,
            region_code="TT",
            price=Decimal("13.75"),
            currency="TTD",
            observed_at=now_utc(),
            source="pytest_history",
            raw_region="Test Region",
            raw_area="Test Area",
            raw_store_name=store.name,
            raw_item_name=second_identity.clean_name,
            match_confidence=1.0,
            raw_payload={"test": True},
        )
    )
    db_session.commit()
    return {"selection_key": selection_key, "family_a": family_a, "family_b": family_b, "product_b": product_b}


def test_product_selection_review_group_lists_shared_selection_keys(db_session: Session, product_review_fixture):
    groups = list_product_selection_groups(db_session, q=product_review_fixture["selection_key"], limit=10, offset=0)

    assert len(groups) == 1
    group = groups[0]
    assert group["selection_key"] == product_review_fixture["selection_key"]
    assert group["product_family_count"] == 2
    assert group["current_listing_count"] == 1
    assert group["historical_observation_count"] == 1


def test_product_selection_review_detail_shows_products_listings_and_observations(db_session: Session, product_review_fixture):
    detail = product_selection_group_detail(db_session, product_review_fixture["selection_key"])

    assert len(detail["canonical_products"]) == 2
    assert len(detail["current_listings"]) == 1
    assert len(detail["historical_observations"]) == 1


def test_approve_product_selection_group_consolidates_to_target_family(db_session: Session, product_review_fixture):
    review = approve_product_selection_group(
        db_session,
        product_review_fixture["selection_key"],
        ProductSelectionApprovalRequest(product_family_id=product_review_fixture["family_a"].id, notes="Same product family"),
    )

    db_session.refresh(product_review_fixture["product_b"])
    assert product_review_fixture["product_b"].product_family_id == product_review_fixture["family_a"].id
    assert review.action == "approved_family_consolidation"
    assert review.canonical_products_updated == 1
    assert db_session.get(ProductSelectionReview, review.id) is not None
    assert list_product_selection_groups(db_session, q=product_review_fixture["selection_key"], limit=10, offset=0) == []
