from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Retailer, Store
from app.schemas.api_responses import StoreListResponse

router = APIRouter()


@router.get("/stores", response_model=StoreListResponse)
def stores(q: str | None = None, limit: int = 500, offset: int = 0, db: Session = Depends(get_db)) -> StoreListResponse:
    query = db.query(Store).join(Retailer).order_by(Retailer.name, Store.name)
    if q:
        query = query.filter(Store.name.ilike(f"%{q}%"))
    items = query.limit(limit).offset(offset).all()
    return StoreListResponse(
        items=[
            {
                "id": item.id,
                "name": item.name,
                "retailer_id": item.retailer_id,
                "retailer_name": item.retailer.name if item.retailer else None,
                "address": item.address,
                "latitude": item.latitude,
                "longitude": item.longitude,
                "is_active": item.is_active,
            }
            for item in items
        ]
    )
