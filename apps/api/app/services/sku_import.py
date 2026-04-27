from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Brand, ImportBatch, ImportRowError, SKU
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


def _to_decimal(value: object, column_name: str) -> Decimal:
    if value is None or pd.isna(value):
        raise ValueError(f"{column_name} is required")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {column_name}") from exc


def _to_bool(value: object, column_name: str, default: bool) -> bool:
    if value is None or pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value for {column_name}")


def _required_text(value: object, column_name: str) -> str:
    if value is None or pd.isna(value):
        raise ValueError(f"{column_name} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{column_name} is required")
    return text


def _optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def import_sku_master(db: Session, brand_id: int, file_name: str, content: bytes) -> ImportSummaryResponse:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand {brand_id} does not exist. Create the brand before importing SKUs.",
        )

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
    sku_cache: dict[str, SKU] = {}

    for row_idx, row in df.iterrows():
        row_number = int(row_idx) + 2
        try:
            sku_code = _required_text(row.get("sku_code"), "sku_code")
            sku_name = _required_text(row.get("sku_name"), "sku_name")
            category = _required_text(row.get("category"), "category")

            selling_price = _to_decimal(row.get("selling_price"), "selling_price")
            contribution_margin = _to_decimal(row.get("contribution_margin"), "contribution_margin")
            case_pack = _to_decimal(row.get("case_pack"), "case_pack")
            brand = _optional_text(row.get("brand")) if "brand" in df.columns else None
            is_hero_sku = _to_bool(row.get("is_hero_sku"), column_name="is_hero_sku", default=False)
            active_flag = _to_bool(row.get("active_flag"), column_name="active_flag", default=True)

            mrp_value = row.get("mrp")
            mrp = None
            if "mrp" in df.columns and not (mrp_value is None or pd.isna(mrp_value)):
                mrp = _to_decimal(mrp_value, "mrp")

            existing = sku_cache.get(sku_code)
            if existing is None:
                existing = db.scalar(select(SKU).where(SKU.brand_id == brand_id, SKU.sku_code == sku_code))
                if existing is not None:
                    sku_cache[sku_code] = existing
            if existing is not None:
                duplicate_rows += 1
                existing.sku_name = sku_name
                existing.category = category
                existing.selling_price = selling_price
                existing.contribution_margin = contribution_margin
                existing.case_pack = case_pack
                existing.brand = brand
                existing.mrp = mrp
                existing.is_hero_sku = is_hero_sku
                existing.active_flag = active_flag
            else:
                sku = SKU(
                    brand_id=brand_id,
                    sku_code=sku_code,
                    sku_name=sku_name,
                    category=category,
                    selling_price=selling_price,
                    contribution_margin=contribution_margin,
                    case_pack=case_pack,
                    brand=brand,
                    mrp=mrp,
                    is_hero_sku=is_hero_sku,
                    active_flag=active_flag,
                )
                db.add(sku)
                sku_cache[sku_code] = sku
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
