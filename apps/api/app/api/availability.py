from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import AvailabilitySnapshot, Location, SKU
from app.schemas.imports import AvailabilitySnapshotResponse, LocationSchema

router = APIRouter(tags=["availability"])


@router.get("/availability", response_model=list[AvailabilitySnapshotResponse])
def list_availability(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[AvailabilitySnapshotResponse]:
    stmt: Select[tuple[AvailabilitySnapshot, SKU, Location]] = (
        select(AvailabilitySnapshot, SKU, Location)
        .join(SKU, AvailabilitySnapshot.sku_id == SKU.id)
        .join(Location, AvailabilitySnapshot.location_id == Location.id)
        .where(AvailabilitySnapshot.brand_id == brand_id)
        .order_by(AvailabilitySnapshot.timestamp.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(Location.platform == platform)
    if city:
        stmt = stmt.where(Location.city == city)
    if status:
        stmt = stmt.where(AvailabilitySnapshot.status == status)

    rows = db.execute(stmt).all()
    return [
        AvailabilitySnapshotResponse(
            id=snapshot.id,
            brand_id=snapshot.brand_id,
            sku_id=snapshot.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            status=snapshot.status,
            timestamp=snapshot.timestamp,
            import_batch_id=snapshot.import_batch_id,
            location=LocationSchema(
                id=location.id,
                platform=location.platform,
                city=location.city,
                location=location.location,
            ),
        )
        for snapshot, sku, location in rows
    ]
