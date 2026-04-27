from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RowErrorSchema(BaseModel):
    row_number: int
    column_name: str
    error_code: str
    error_message: str


class ImportSummaryResponse(BaseModel):
    import_batch_id: int
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    errors: list[RowErrorSchema]


class SKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    sku_code: str
    sku_name: str
    category: str
    selling_price: Decimal
    contribution_margin: Decimal
    case_pack: Decimal
    brand: str | None
    mrp: Decimal | None
    is_hero_sku: bool
    active_flag: bool
    created_at: datetime
    updated_at: datetime


class LocationSchema(BaseModel):
    id: int
    platform: str
    city: str
    location: str


class AvailabilitySnapshotResponse(BaseModel):
    id: int
    brand_id: int
    sku_id: int
    sku_code: str
    sku_name: str
    status: str
    timestamp: datetime
    import_batch_id: int | None
    location: LocationSchema


class SalesVelocityResponse(BaseModel):
    id: int
    brand_id: int
    sku_id: int
    sku_code: str
    sku_name: str
    platform: str
    city: str
    avg_units_per_day: Decimal
    import_batch_id: int | None
    created_at: datetime
    updated_at: datetime


class InventoryPositionResponse(BaseModel):
    id: int
    brand_id: int
    sku_id: int
    sku_code: str
    sku_name: str
    warehouse: str
    city: str
    available_qty: Decimal
    timestamp: datetime
    import_batch_id: int | None
    created_at: datetime
    updated_at: datetime
