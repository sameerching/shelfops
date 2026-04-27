from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import SKU
from app.schemas.imports import SKUResponse

router = APIRouter(tags=["skus"])


@router.get("/skus", response_model=list[SKUResponse])
def list_skus(brand_id: int = Query(...), db: Session = Depends(get_db_session)) -> list[SKU]:
    rows = db.scalars(select(SKU).where(SKU.brand_id == brand_id).order_by(SKU.sku_code.asc())).all()
    return list(rows)
