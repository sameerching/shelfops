from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import PORecord, SKU
from app.schemas.imports import PORecordResponse

router = APIRouter(tags=["po-records"])


@router.get("/po-records", response_model=list[PORecordResponse])
def list_po_records(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[PORecordResponse]:
    stmt: Select[tuple[PORecord, SKU]] = (
        select(PORecord, SKU)
        .join(SKU, PORecord.sku_id == SKU.id)
        .where(PORecord.brand_id == brand_id)
        .order_by(PORecord.po_date.desc(), PORecord.updated_at.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(PORecord.platform == platform)
    if city:
        stmt = stmt.where(PORecord.city == city)

    rows = db.execute(stmt).all()
    return [
        PORecordResponse(
            id=record.id,
            brand_id=record.brand_id,
            sku_id=record.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            platform=record.platform,
            city=record.city,
            po_number=record.po_number,
            po_qty=record.po_qty,
            po_status=record.po_status,
            po_date=record.po_date,
            import_batch_id=record.import_batch_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record, sku in rows
    ]
