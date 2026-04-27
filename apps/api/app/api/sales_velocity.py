from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import SKU, SalesVelocity
from app.schemas.imports import SalesVelocityResponse

router = APIRouter(tags=["sales-velocity"])


@router.get("/sales-velocity", response_model=list[SalesVelocityResponse])
def list_sales_velocity(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[SalesVelocityResponse]:
    stmt: Select[tuple[SalesVelocity, SKU]] = (
        select(SalesVelocity, SKU)
        .join(SKU, SalesVelocity.sku_id == SKU.id)
        .where(SalesVelocity.brand_id == brand_id)
        .order_by(SalesVelocity.updated_at.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(SalesVelocity.platform == platform)
    if city:
        stmt = stmt.where(SalesVelocity.city == city)

    rows = db.execute(stmt).all()
    return [
        SalesVelocityResponse(
            id=sales_velocity.id,
            brand_id=sales_velocity.brand_id,
            sku_id=sales_velocity.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            platform=sales_velocity.platform,
            city=sales_velocity.city,
            avg_units_per_day=sales_velocity.avg_units_per_day,
            import_batch_id=sales_velocity.import_batch_id,
            created_at=sales_velocity.created_at,
            updated_at=sales_velocity.updated_at,
        )
        for sales_velocity, sku in rows
    ]
