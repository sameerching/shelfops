from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import InventoryPosition, SKU
from app.schemas.imports import InventoryPositionResponse

router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_model=list[InventoryPositionResponse])
def list_inventory(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[InventoryPositionResponse]:
    stmt: Select[tuple[InventoryPosition, SKU]] = (
        select(InventoryPosition, SKU)
        .join(SKU, InventoryPosition.sku_id == SKU.id)
        .where(InventoryPosition.brand_id == brand_id)
        .order_by(InventoryPosition.timestamp.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if warehouse:
        stmt = stmt.where(InventoryPosition.warehouse == warehouse)
    if city:
        stmt = stmt.where(InventoryPosition.city == city)

    rows = db.execute(stmt).all()
    return [
        InventoryPositionResponse(
            id=inventory.id,
            brand_id=inventory.brand_id,
            sku_id=inventory.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            warehouse=inventory.warehouse,
            city=inventory.city,
            available_qty=inventory.available_qty,
            timestamp=inventory.timestamp,
            import_batch_id=inventory.import_batch_id,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
        )
        for inventory, sku in rows
    ]
