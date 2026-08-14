from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.compilation import CompilationService

router = APIRouter(prefix="/compilation", tags=["compilation"])


@router.post("")
@router.post("/")
def compile_plan(
    grocery_list_id: UUID,
    fulfillment_method: str,
    start_location: dict,
    transit_mode: str = "driving",
    radius: float = 50000.0,
    db: Session = Depends(get_db),
):
    service = CompilationService(db)
    try:
        plan = service.compile_plan(
            grocery_list_id,
            fulfillment_method,
            start_location,
            transit_mode,
            radius,
        )
        return plan
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
