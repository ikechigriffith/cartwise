from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Retailer

router = APIRouter()


@router.get("/retailers")
def retailers(limit: int = 500, offset: int = 0, db: Session = Depends(get_db)) -> dict:
    items = db.query(Retailer).order_by(Retailer.name).limit(limit).offset(offset).all()
    return {"items": [{"id": item.id, "name": item.name} for item in items]}
