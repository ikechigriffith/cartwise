import uuid
from typing import Any

from pydantic import BaseModel


class ProductSelectionApprovalRequest(BaseModel):
    product_family_id: uuid.UUID
    reviewed_by: uuid.UUID | None = None
    notes: str | None = None
    fields_changed: dict[str, Any] | None = None
