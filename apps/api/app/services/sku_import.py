from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ImportBatch, ImportRowError, SKU
from app.schemas.imports import ImportSummaryResponse, RowErrorSchema

REQUIRED_COLUMNS = {
    "sku_code",
    "sku_name",
    "category",
    "selling_price",
    "contribution_margin",
    "case_pack",
}
OPTIONAL_COLUMNS = {"brand", "mrp", "is_hero_sku", "active_flag"}


TRUE_VALUES = {"1", "true", "t", "yes", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n"}


def parse_sku_file(filename: str, data: bytes) -> pd.DataFrame:
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        df = pd.read_csv(BytesIO(data))
    elif lowered.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(data), engine="openpyxl")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and XLSX are supported")

    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _to_decimal(value: object, column_name: str) -> Decimal:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"{column_name} is required")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {column_name}") from exc


def _to_bool(value: object, default: bool) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError("Invalid boolean value")


def import_sku_master(db: Session, brand_id: int, file_name: str, content: bytes) -> ImportSummaryResponse:
    batch = ImportBatch(brand_id=brand_id, file_type="sku_master", file_name=file_name, status="processing")
    db.add(batch)
    db.flush()

    errors: list[ImportRowError] = []

    df = parse_sku_file(file_name, content)
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
    seen_keys: set[str] = set()

    for row_idx, row in df.iterrows():
        row_number = int(row_idx) + 2
        try:
            sku_code = str(row.get("sku_code", "")).strip()
            sku_name = str(row.get("sku_name", "")).strip()
            category = str(row.get("category", "")).strip()

            if not sku_code:
                raise ValueError("sku_code is required")
            if not sku_name:
                raise ValueError("sku_name is required")
            if not category:
                raise ValueError("category is required")

            selling_price = _to_decimal(row.get("selling_price"), "selling_price")
            contribution_margin = _to_decimal(row.get("contribution_margin"), "contribution_margin")
            case_pack = _to_decimal(row.get("case_pack"), "case_pack")

            mrp_value = row.get("mrp")
            mrp = None
            if "mrp" in df.columns and not (mrp_value is None or (isinstance(mrp_value, float) and pd.isna(mrp_value))):
                mrp = _to_decimal(mrp_value, "mrp")

            key = f"{brand_id}:{sku_code}"
            if key in seen_keys:
                duplicate_rows += 1
            seen_keys.add(key)

            existing = db.scalar(select(SKU).where(SKU.brand_id == brand_id, SKU.sku_code == sku_code))
            if existing is not None:
                duplicate_rows += 1
                existing.sku_name = sku_name
                existing.category = category
                existing.selling_price = selling_price
                existing.contribution_margin = contribution_margin
                existing.case_pack = case_pack
                existing.brand = str(row.get("brand")).strip() if "brand" in df.columns and not pd.isna(row.get("brand")) else None
                existing.mrp = mrp
                existing.is_hero_sku = _to_bool(row.get("is_hero_sku"), default=False)
                existing.active_flag = _to_bool(row.get("active_flag"), default=True)
            else:
                sku = SKU(
                    brand_id=brand_id,
                    sku_code=sku_code,
                    sku_name=sku_name,
                    category=category,
                    selling_price=selling_price,
                    contribution_margin=contribution_margin,
                    case_pack=case_pack,
                    brand=str(row.get("brand")).strip() if "brand" in df.columns and not pd.isna(row.get("brand")) else None,
                    mrp=mrp,
                    is_hero_sku=_to_bool(row.get("is_hero_sku"), default=False),
                    active_flag=_to_bool(row.get("active_flag"), default=True),
                )
                db.add(sku)
            accepted_rows += 1
        except ValueError as exc:
            rejected_rows += 1
            column_name = "unknown"
            message = str(exc)
            if " for " in message:
                column_name = message.split(" for ")[-1]
            elif " is required" in message:
                column_name = message.split(" is required")[0]
            errors.append(
                ImportRowError(
                    import_batch_id=batch.id,
                    row_number=row_number,
                    column_name=column_name,
                    error_code="invalid_value",
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
