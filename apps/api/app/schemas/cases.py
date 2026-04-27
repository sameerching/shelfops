from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CaseGenerateRequest(BaseModel):
    brand_id: int


class StockoutCaseResponse(BaseModel):
    id: int
    sku_code: str
    sku_name: str
    platform: str
    city: str
    location: str
    status: str
    priority: str
    detected_at: datetime
    last_seen_oos_at: datetime
    recovered_at: datetime | None
    stockout_duration_hours: Decimal
    estimated_lost_sales: Decimal
    estimated_lost_margin: Decimal


class CaseGenerateResponse(BaseModel):
    generated_cases: int
    updated_cases: int
    recovered_cases: int
    cases: list[StockoutCaseResponse]
