import uuid
from typing import Any

from pydantic import BaseModel, Field


class CandidateResolutionRequest(BaseModel):
    store_id: uuid.UUID | None = None
    reviewed_by: uuid.UUID | None = None
    notes: str | None = None
    fields_changed: dict[str, Any] | None = None


class CreateStoreFromCandidateRequest(BaseModel):
    retailer_id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    address: dict[str, Any] = Field(default_factory=dict)
    store_type: str = "supermarket"
    reviewed_by: uuid.UUID | None = None
    notes: str | None = None
