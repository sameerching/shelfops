from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import DispatchRecord, SKU
from app.schemas.imports import DispatchRecordResponse

router = APIRouter(tags=["dispatch-records"])


@router.get("/dispatch-records", response_model=list[DispatchRecordResponse])
def list_dispatch_records(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[DispatchRecordResponse]:
    stmt: Select[tuple[DispatchRecord, SKU]] = (
        select(DispatchRecord, SKU)
        .join(SKU, DispatchRecord.sku_id == SKU.id)
        .where(DispatchRecord.brand_id == brand_id)
        .order_by(DispatchRecord.dispatch_date.desc(), DispatchRecord.updated_at.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(DispatchRecord.platform == platform)
    if city:
        stmt = stmt.where(DispatchRecord.city == city)

    rows = db.execute(stmt).all()
    return [
        DispatchRecordResponse(
            id=record.id,
            brand_id=record.brand_id,
            sku_id=record.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            platform=record.platform,
            city=record.city,
            dispatch_qty=record.dispatch_qty,
            dispatch_status=record.dispatch_status,
            dispatch_date=record.dispatch_date,
            import_batch_id=record.import_batch_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record, sku in rows
    ]
