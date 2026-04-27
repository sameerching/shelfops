from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Brand, GRNRecord, ImportBatch, ImportRowError, SKU
from app.schemas.imports import ImportSummaryResponse, RowErrorSchema

REQUIRED_COLUMNS = {"sku_code", "platform", "city", "grn_qty", "grn_status", "grn_date"}


def parse_grn_file(filename: str, data: bytes) -> pd.DataFrame:
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


def _parse_qty(value: object) -> Decimal:
    if value is None or pd.isna(value):
        raise ValueError("grn_qty is required")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid numeric value for grn_qty") from exc
    if not parsed.is_finite():
        raise ValueError("Invalid numeric value for grn_qty")
    if parsed < 0:
        raise ValueError("grn_qty cannot be negative")
    return parsed


def _parse_date(value: object):
    text = _required_text(value, "grn_date")
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
        if re.fullmatch(r"\d{8}", text):
            parsed_numeric = pd.to_datetime(text, format="%Y%m%d", utc=True, errors="coerce")
            if not pd.isna(parsed_numeric):
                return parsed_numeric.date()
        raise ValueError("Invalid date value for grn_date")
    parsed = pd.to_datetime(text, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("Invalid date value for grn_date")
    return parsed.date()


def import_grn_report(db: Session, brand_id: int, file_name: str, content: bytes) -> ImportSummaryResponse:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand {brand_id} does not exist. Create the brand before importing GRN tracker.",
        )

    batch = ImportBatch(brand_id=brand_id, file_type="grn_tracker", file_name=file_name, status="processing")
    db.add(batch)
    db.flush()

    errors: list[ImportRowError] = []
    df = parse_grn_file(file_name, content)

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
    dedupe_cache: set[tuple[int, str, str, object, str]] = set()

    for row_idx, row in df.iterrows():
        row_number = int(row_idx) + 2
        try:
            sku_code = _required_text(row.get("sku_code"), "sku_code")
            platform = _required_text(row.get("platform"), "platform")
            city = _required_text(row.get("city"), "city")
            grn_qty = _parse_qty(row.get("grn_qty"))
            grn_status = _required_text(row.get("grn_status"), "grn_status")
            grn_date = _parse_date(row.get("grn_date"))

            sku = sku_cache.get(sku_code)
            if sku_code not in sku_cache:
                sku = db.scalar(select(SKU).where(SKU.brand_id == brand_id, SKU.sku_code == sku_code))
                sku_cache[sku_code] = sku
            if sku is None:
                raise ValueError("Unknown sku_code for brand")

            dedupe_key = (sku.id, platform, city, grn_date, file_name)
            if dedupe_key in dedupe_cache:
                duplicate_rows += 1
                continue

            existing = db.scalar(
                select(GRNRecord)
                .where(
                    GRNRecord.brand_id == brand_id,
                    GRNRecord.sku_id == sku.id,
                    GRNRecord.platform == platform,
                    GRNRecord.city == city,
                    GRNRecord.grn_date == grn_date,
                    GRNRecord.source_file == file_name,
                )
            )
            if existing is not None:
                duplicate_rows += 1
                dedupe_cache.add(dedupe_key)
                continue

            db.add(
                GRNRecord(
                    brand_id=brand_id,
                    sku_id=sku.id,
                    platform=platform,
                    city=city,
                    grn_qty=grn_qty,
                    grn_status=grn_status,
                    grn_date=grn_date,
                    source_file=file_name,
                    import_batch_id=batch.id,
                )
            )
            dedupe_cache.add(dedupe_key)
            accepted_rows += 1
        except ValueError as exc:
            rejected_rows += 1
            message = str(exc)
            if message == "Unknown sku_code for brand":
                column_name = "sku_code"
                error_code = "unknown_sku_code"
            elif message == "Invalid numeric value for grn_qty":
                column_name = "grn_qty"
                error_code = "invalid_numeric"
            elif message == "grn_qty cannot be negative":
                column_name = "grn_qty"
                error_code = "negative_value"
            elif message == "Invalid date value for grn_date":
                column_name = "grn_date"
                error_code = "invalid_date"
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
