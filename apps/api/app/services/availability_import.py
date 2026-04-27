from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AvailabilitySnapshot, Brand, ImportBatch, ImportRowError, Location, SKU
from app.schemas.imports import ImportSummaryResponse, RowErrorSchema

REQUIRED_COLUMNS = {"sku_code", "platform", "city", "location", "status", "timestamp"}

OUT_OF_STOCK_VALUES = {
    "oos",
    "out_of_stock",
    "out of stock",
    "unavailable",
    "not_available",
    "not available",
}

IN_STOCK_VALUES = {"in_stock", "in stock", "available", "instock", "yes"}


def parse_availability_file(filename: str, data: bytes) -> pd.DataFrame:
    lowered = filename.lower()
    if not (lowered.endswith(".csv") or lowered.endswith(".xlsx")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and XLSX are supported")

    try:
        if lowered.endswith(".csv"):
            df = pd.read_csv(BytesIO(data), dtype=str)
        else:
            df = pd.read_excel(BytesIO(data), engine="openpyxl", dtype=str)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse uploaded file. Please upload a valid CSV or XLSX file.",
        ) from exc

    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _required_text(value: object, column_name: str) -> str:
    if value is None or pd.isna(value):
        raise ValueError(f"{column_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{column_name} is required")
    return text


def _normalize_status(value: object) -> str:
    text = _required_text(value, "status").lower()
    if text in OUT_OF_STOCK_VALUES:
        return "out_of_stock"
    if text in IN_STOCK_VALUES:
        return "in_stock"
    raise ValueError("Invalid status value")


def _parse_timestamp(value: object) -> datetime:
    text = _required_text(value, "timestamp")
    parsed = pd.to_datetime(text, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("Invalid timestamp value")
    return parsed.to_pydatetime().astimezone(UTC)


def import_availability_report(db: Session, brand_id: int, file_name: str, content: bytes) -> ImportSummaryResponse:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand {brand_id} does not exist. Create the brand before importing availability.",
        )

    batch = ImportBatch(brand_id=brand_id, file_type="availability", file_name=file_name, status="processing")
    db.add(batch)
    db.flush()

    errors: list[ImportRowError] = []
    df = parse_availability_file(file_name, content)

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        batch.status = "failed"
        batch.total_rows = int(len(df.index))
        batch.rejected_rows = batch.total_rows
        for column in missing_columns:
            errors.append(
                ImportRowError(
                    import_batch_id=batch.id,
                    row_number=0,
                    column_name=column,
                    error_code="missing_required_column",
                    error_message=f"Missing required column: {column}",
                )
            )
        db.add_all(errors)
        db.commit()
        return ImportSummaryResponse(
            import_batch_id=batch.id,
            total_rows=batch.total_rows,
            accepted_rows=0,
            rejected_rows=batch.rejected_rows,
            duplicate_rows=0,
            errors=[
                RowErrorSchema(
                    row_number=e.row_number,
                    column_name=e.column_name,
                    error_code=e.error_code,
                    error_message=e.error_message,
                )
                for e in errors
            ],
        )

    total_rows = int(len(df.index))
    accepted_rows = 0
    rejected_rows = 0
    duplicate_rows = 0

    sku_cache: dict[str, SKU | None] = {}
    location_cache: dict[tuple[str, str, str], Location] = {}
    snapshot_cache: set[tuple[int, int, datetime]] = set()

    for row_idx, row in df.iterrows():
        row_number = int(row_idx) + 2
        try:
            sku_code = _required_text(row.get("sku_code"), "sku_code")
            platform = _required_text(row.get("platform"), "platform")
            city = _required_text(row.get("city"), "city")
            location_name = _required_text(row.get("location"), "location")
            status_value = _normalize_status(row.get("status"))
            snapshot_ts = _parse_timestamp(row.get("timestamp"))

            sku = sku_cache.get(sku_code)
            if sku_code not in sku_cache:
                sku = db.scalar(select(SKU).where(SKU.brand_id == brand_id, SKU.sku_code == sku_code))
                sku_cache[sku_code] = sku
            if sku is None:
                raise ValueError("Unknown sku_code for brand")

            loc_key = (platform, city, location_name)
            location = location_cache.get(loc_key)
            if location is None:
                location = db.scalar(
                    select(Location).where(
                        Location.platform == platform,
                        Location.city == city,
                        Location.location == location_name,
                    )
                )
                if location is None:
                    location = Location(platform=platform, city=city, location=location_name)
                    db.add(location)
                    db.flush()
                location_cache[loc_key] = location

            dedupe_key = (sku.id, location.id, snapshot_ts)
            if dedupe_key in snapshot_cache:
                duplicate_rows += 1
                continue

            existing = db.scalar(
                select(AvailabilitySnapshot).where(
                    AvailabilitySnapshot.brand_id == brand_id,
                    AvailabilitySnapshot.sku_id == sku.id,
                    AvailabilitySnapshot.location_id == location.id,
                    AvailabilitySnapshot.timestamp == snapshot_ts,
                )
            )
            if existing is not None:
                duplicate_rows += 1
                snapshot_cache.add(dedupe_key)
                continue

            db.add(
                AvailabilitySnapshot(
                    brand_id=brand_id,
                    sku_id=sku.id,
                    location_id=location.id,
                    status=status_value,
                    timestamp=snapshot_ts,
                    import_batch_id=batch.id,
                )
            )
            snapshot_cache.add(dedupe_key)
            accepted_rows += 1
        except ValueError as exc:
            rejected_rows += 1
            message = str(exc)
            if message == "Unknown sku_code for brand":
                column_name = "sku_code"
                error_code = "unknown_sku_code"
            elif message == "Invalid status value":
                column_name = "status"
                error_code = "invalid_status"
            elif message == "Invalid timestamp value":
                column_name = "timestamp"
                error_code = "invalid_timestamp"
            elif message.endswith(" is required"):
                column_name = message.replace(" is required", "")
                error_code = "missing_required_value"
            else:
                column_name = "unknown"
                error_code = "invalid_value"

            errors.append(
                ImportRowError(
                    import_batch_id=batch.id,
                    row_number=row_number,
                    column_name=column_name,
                    error_code=error_code,
                    error_message=message,
                )
            )

    batch.status = "completed" if rejected_rows == 0 else "completed_with_errors"
    batch.total_rows = total_rows
    batch.accepted_rows = accepted_rows
    batch.rejected_rows = rejected_rows
    batch.duplicate_rows = duplicate_rows

    if errors:
        db.add_all(errors)
    db.commit()

    return ImportSummaryResponse(
        import_batch_id=batch.id,
        total_rows=total_rows,
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        duplicate_rows=duplicate_rows,
        errors=[
            RowErrorSchema(
                row_number=e.row_number,
                column_name=e.column_name,
                error_code=e.error_code,
                error_message=e.error_message,
            )
            for e in errors
        ],
    )
