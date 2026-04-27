from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import GRNRecord, SKU
from app.schemas.imports import GRNRecordResponse

router = APIRouter(tags=["grn-records"])


@router.get("/grn-records", response_model=list[GRNRecordResponse])
def list_grn_records(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[GRNRecordResponse]:
    stmt: Select[tuple[GRNRecord, SKU]] = (
        select(GRNRecord, SKU)
        .join(SKU, GRNRecord.sku_id == SKU.id)
        .where(GRNRecord.brand_id == brand_id)
        .order_by(GRNRecord.grn_date.desc(), GRNRecord.updated_at.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(GRNRecord.platform == platform)
    if city:
        stmt = stmt.where(GRNRecord.city == city)

    rows = db.execute(stmt).all()
    return [
        GRNRecordResponse(
            id=record.id,
            brand_id=record.brand_id,
            sku_id=record.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            platform=record.platform,
            city=record.city,
            grn_qty=record.grn_qty,
            grn_status=record.grn_status,
            grn_date=record.grn_date,
            import_batch_id=record.import_batch_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record, sku in rows
    ]
