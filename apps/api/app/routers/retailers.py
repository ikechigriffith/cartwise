from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Retailer
from app.schemas.api_responses import RetailerListResponse

router = APIRouter()


@router.get("/retailers", response_model=RetailerListResponse)
def retailers(limit: int = 500, offset: int = 0, db: Session = Depends(get_db)) -> RetailerListResponse:
    items = db.query(Retailer).order_by(Retailer.name).limit(limit).offset(offset).all()
    return RetailerListResponse(items=[{"id": item.id, "name": item.name} for item in items])
