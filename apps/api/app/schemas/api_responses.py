from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RetailerItem(BaseModel):
    id: UUID
    name: str


class RetailerListResponse(BaseModel):
    items: list[RetailerItem]


class StoreItem(BaseModel):
    id: UUID
    name: str
    retailer_id: UUID
    retailer_name: str | None = None
    address: dict | None = None
    latitude: float
    longitude: float
    is_active: bool


class StoreListResponse(BaseModel):
    items: list[StoreItem]


class ProductSearchItem(BaseModel):
    id: str
    canonical_name: str
    brand: str | None = None
    normalized_brand: str | None = None
    selection_key: str | None = None
    size_value: float | None = None
    size_unit: str | None = None
    package_quantity: int | None = None
    product_family_name: str
    product_family_selection_key: str | None = None
    current_listing_count: int = 0
    in_stock_listing_count: int = 0
    current_min_price: float | None = None
    latest_price_checked_at: datetime | None = None
    historical_observation_count: int = 0
    latest_historical_observed_at: datetime | None = None


class ProductSearchResponse(BaseModel):
    items: list[ProductSearchItem]
