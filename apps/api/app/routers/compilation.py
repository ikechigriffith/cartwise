from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.deps import get_db
from app.services.compilation import CompilationService

router = APIRouter(prefix="/compilation", tags=["compilation"])

@router.post("/")
async def compile_plan(
    grocery_list_id: UUID,
    fulfillment_method: str,
    start_location: dict,
    transit_mode: Optional[str] = "driving",
    radius: Optional[float] = 50000.0,
    db: AsyncSession = Depends(get_db)
):
    service = CompilationService(db)
    try:
        plan = await service.compile_plan(
            grocery_list_id,
            fulfillment_method,
            start_location,
            transit_mode,
            radius
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
