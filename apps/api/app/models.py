import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    default_start_location: Mapped[dict | None] = mapped_column(JSONB)
    default_radius: Mapped[float | None] = mapped_column(Float)
    default_transit_mode: Mapped[str | None] = mapped_column(String(50))
    substitution_preferences: Mapped[dict | None] = mapped_column(JSONB)

    grocery_lists: Mapped[list["GroceryList"]] = relationship(back_populates="user")


class Retailer(TimestampMixin, Base):
    __tablename__ = "retailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    website_url: Mapped[str | None] = mapped_column(Text)
    integration_type: Mapped[str] = mapped_column(String(50), default="scrape")
    loyalty_program_supported: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_info: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))

    stores: Mapped[list["Store"]] = relationship(back_populates="retailer")
    data_sources: Mapped[list["RetailerDataSource"]] = relationship(back_populates="retailer")


class RetailerDataSource(TimestampMixin, Base):
    __tablename__ = "retailer_data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("retailers.id"), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), default="website")
    has_product_catalog: Mapped[bool | None] = mapped_column(Boolean)
    has_prices: Mapped[bool | None] = mapped_column(Boolean)
    has_stock: Mapped[bool | None] = mapped_column(Boolean)
    requires_login: Mapped[bool | None] = mapped_column(Boolean)
    scrape_status: Mapped[str] = mapped_column(String(50), default="needs_verification", index=True)
    confidence: Mapped[str] = mapped_column(String(50), default="unknown")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    retailer: Mapped[Retailer] = relationship(back_populates="data_sources")


class SourceDocument(TimestampMixin, Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str | None] = mapped_column(Text)
    post_id: Mapped[str | None] = mapped_column(String(100), index=True)
    post_url: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str | None] = mapped_column(String(50), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    local_path: Mapped[str | None] = mapped_column(Text)
    file_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    import_status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)
    observations_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)


class ImportRun(TimestampMixin, Base):
    __tablename__ = "import_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_documents: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_documents: Mapped[int] = mapped_column(Integer, default=0)
    observations_inserted: Mapped[int] = mapped_column(Integer, default=0)
    observations_skipped: Mapped[int] = mapped_column(Integer, default=0)
    matched_store_observations: Mapped[int] = mapped_column(Integer, default=0)
    retailer_only_observations: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_observations: Mapped[int] = mapped_column(Integer, default=0)
    raw_summary: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)


class StoreCandidate(TimestampMixin, Base):
    __tablename__ = "store_candidates"
    __table_args__ = (
        UniqueConstraint("source", "raw_store_name", "raw_area", "raw_region", name="uq_store_candidate_source_raw_location"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), index=True)
    raw_store_name: Mapped[str] = mapped_column(String(300), index=True)
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    raw_area: Mapped[str | None] = mapped_column(String(200), index=True)
    raw_region: Mapped[str | None] = mapped_column(String(100), index=True)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("retailers.id"), index=True)
    matched_store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="needs_review", index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    observations_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    retailer: Mapped[Retailer | None] = relationship()
    matched_store: Mapped["Store | None"] = relationship()


class StoreAlias(TimestampMixin, Base):
    __tablename__ = "store_aliases"
    __table_args__ = (
        UniqueConstraint("source", "raw_name", "raw_area", "raw_region", name="uq_store_alias_source_raw_location"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    raw_name: Mapped[str] = mapped_column(String(300), index=True)
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    raw_area: Mapped[str | None] = mapped_column(String(200), index=True)
    raw_region: Mapped[str | None] = mapped_column(String(100), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    store: Mapped["Store"] = relationship(back_populates="aliases")


class StoreCandidateReview(TimestampMixin, Base):
    __tablename__ = "store_candidate_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("store_candidates.id"), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    existing_store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    created_store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    fields_changed: Mapped[dict | None] = mapped_column(JSONB)
    observations_backfilled: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[StoreCandidate] = relationship()
    existing_store: Mapped["Store | None"] = relationship(foreign_keys=[existing_store_id])
    created_store: Mapped["Store | None"] = relationship(foreign_keys=[created_store_id])


class Store(TimestampMixin, Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("retailers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    store_type: Mapped[str] = mapped_column(String(50))
    address: Mapped[dict] = mapped_column(JSONB)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    contact_info: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    service_capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    store_hours: Mapped[dict | None] = mapped_column(JSONB)
    transit_accessibility: Mapped[dict | None] = mapped_column(JSONB)
    external_source: Mapped[str | None] = mapped_column(String(50), index=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    raw_tags: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    retailer: Mapped[Retailer] = relationship(back_populates="stores")
    listings: Mapped[list["ProductListing"]] = relationship(back_populates="store")
    aliases: Mapped[list["StoreAlias"]] = relationship(back_populates="store")


class ProductFamily(TimestampMixin, Base):
    __tablename__ = "product_families"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(300), index=True)
    selection_key: Mapped[str | None] = mapped_column(String(300), index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), index=True)
    common_aliases: Mapped[list] = mapped_column(JSONB, default=list)
    default_unit: Mapped[str | None] = mapped_column(String(50))

    canonical_products: Mapped[list["CanonicalProduct"]] = relationship(back_populates="product_family")


class CanonicalProduct(TimestampMixin, Base):
    __tablename__ = "canonical_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_families.id"), index=True)
    canonical_name: Mapped[str] = mapped_column(String(300), index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(500), index=True)
    selection_key: Mapped[str | None] = mapped_column(String(500), index=True)
    brand: Mapped[str | None] = mapped_column(String(150), index=True)
    normalized_brand: Mapped[str | None] = mapped_column(String(150), index=True)
    is_store_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    owning_retailer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("retailers.id"))
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), index=True)
    size_value: Mapped[float | None] = mapped_column(Float)
    size_unit: Mapped[str | None] = mapped_column(String(50))
    package_quantity: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    requirements_supported: Mapped[list] = mapped_column(JSONB, default=list)
    is_perishable: Mapped[bool] = mapped_column(Boolean, default=False)

    product_family: Mapped[ProductFamily] = relationship(back_populates="canonical_products")
    listings: Mapped[list["ProductMapping"]] = relationship(back_populates="canonical_product")


class ProductPriceObservation(TimestampMixin, Base):
    __tablename__ = "product_price_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canonical_products.id"), index=True)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("retailers.id"), index=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    region_code: Mapped[str | None] = mapped_column(String(50), index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="TTD")
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_region: Mapped[str | None] = mapped_column(String(100), index=True)
    raw_area: Mapped[str | None] = mapped_column(String(200), index=True)
    raw_store_name: Mapped[str | None] = mapped_column(String(300), index=True)
    raw_item_name: Mapped[str | None] = mapped_column(String(500), index=True)
    match_confidence: Mapped[float | None] = mapped_column(Float)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)


class ProductListing(TimestampMixin, Base):
    __tablename__ = "product_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    retailer_product_id: Mapped[str | None] = mapped_column(String(200), index=True)
    raw_name: Mapped[str] = mapped_column(String(500), index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(500), index=True)
    selection_key: Mapped[str | None] = mapped_column(String(500), index=True)
    raw_description: Mapped[str | None] = mapped_column(Text)
    raw_brand: Mapped[str | None] = mapped_column(String(150))
    normalized_brand: Mapped[str | None] = mapped_column(String(150), index=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4))
    package_quantity: Mapped[float | None] = mapped_column(Float)
    unit_size_value: Mapped[float | None] = mapped_column(Float)
    unit_size_unit: Mapped[str | None] = mapped_column(String(50))
    total_size_value: Mapped[float | None] = mapped_column(Float)
    total_size_unit: Mapped[str | None] = mapped_column(String(50))
    normalized_size_value: Mapped[float | None] = mapped_column(Float)
    normalized_size_unit: Mapped[str | None] = mapped_column(String(50))
    computed_price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4))
    computed_price_unit: Mapped[str | None] = mapped_column(String(50))
    unit_price_confidence: Mapped[str | None] = mapped_column(String(50))
    unit_price_needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_availability: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(50), default="scrape")
    source_url: Mapped[str | None] = mapped_column(Text)
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stock_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    store: Mapped[Store] = relationship(back_populates="listings")
    mappings: Mapped[list["ProductMapping"]] = relationship(back_populates="product_listing")


class ProductMapping(TimestampMixin, Base):
    __tablename__ = "product_mappings"
    __table_args__ = (
        UniqueConstraint("product_listing_id", "canonical_product_id", name="uq_product_mappings_listing_canonical"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_listings.id"), index=True)
    canonical_product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canonical_products.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[str] = mapped_column(String(20), index=True)
    mapping_method: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending_review", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    product_listing: Mapped[ProductListing] = relationship(back_populates="mappings")
    canonical_product: Mapped[CanonicalProduct] = relationship(back_populates="listings")


class ProductSelectionReview(TimestampMixin, Base):
    __tablename__ = "product_selection_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    selection_key: Mapped[str] = mapped_column(String(500), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    product_family_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_families.id"), index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    canonical_products_updated: Mapped[int] = mapped_column(Integer, default=0)
    fields_changed: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    product_family: Mapped[ProductFamily | None] = relationship()


class GroceryList(TimestampMixin, Base):
    __tablename__ = "grocery_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="grocery_lists")
    items: Mapped[list["GroceryListItem"]] = relationship(back_populates="grocery_list")


class GroceryListItem(TimestampMixin, Base):
    __tablename__ = "grocery_list_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grocery_list_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grocery_lists.id"), index=True)
    product_family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_families.id"), index=True)
    needed_amount: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    package_flexibility: Mapped[bool] = mapped_column(Boolean, default=True)
    requirements: Mapped[list] = mapped_column(JSONB, default=list)
    preferences: Mapped[list] = mapped_column(JSONB, default=list)
    substitution_overrides: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    grocery_list: Mapped[GroceryList] = relationship(back_populates="items")


class ProposedPlan(TimestampMixin, Base):
    __tablename__ = "proposed_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grocery_list_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grocery_lists.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    fulfillment_method: Mapped[str] = mapped_column(String(50))
    primary_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    planned_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_location: Mapped[dict] = mapped_column(JSONB)
    end_location: Mapped[dict | None] = mapped_column(JSONB)
    radius: Mapped[float] = mapped_column(Float)
    transit_mode: Mapped[str] = mapped_column(String(50))
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    freshness_labels: Mapped[dict] = mapped_column(JSONB, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    alternatives: Mapped[list["PlanAlternative"]] = relationship(back_populates="proposed_plan")


class PlanAlternative(Base):
    __tablename__ = "plan_alternatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposed_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proposed_plans.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    route: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    uses_uncertain_overrides: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_notes: Mapped[list] = mapped_column(JSONB, default=list)

    proposed_plan: Mapped[ProposedPlan] = relationship(back_populates="alternatives")
    stops: Mapped[list["Stop"]] = relationship(back_populates="plan_alternative")


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_alternative_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_alternatives.id"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    estimated_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    store_open_at_arrival: Mapped[bool | None] = mapped_column(Boolean)
    subtotal: Mapped[float | None] = mapped_column(Numeric(10, 2))

    plan_alternative: Mapped[PlanAlternative] = relationship(back_populates="stops")
    item_assignments: Mapped[list["ItemAssignment"]] = relationship(back_populates="stop")


class ItemAssignment(Base):
    __tablename__ = "item_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stops.id"), index=True)
    grocery_list_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grocery_list_items.id"), index=True)
    canonical_product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("canonical_products.id"), index=True)
    product_listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_listings.id"), index=True)
    assigned_quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    estimated_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4))
    substitution_used: Mapped[bool] = mapped_column(Boolean, default=False)
    requirements_satisfied: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences_honored: Mapped[bool] = mapped_column(Boolean, default=True)
    freshness_label: Mapped[str | None] = mapped_column(String(100))
    confidence_notes: Mapped[list] = mapped_column(JSONB, default=list)

    stop: Mapped[Stop] = relationship(back_populates="item_assignments")
