from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.schemas.imports import ImportSummaryResponse
from app.services.availability_import import import_availability_report
from app.services.dispatch_import import import_dispatch_report
from app.services.grn_import import import_grn_report
from app.services.inventory_import import import_inventory_report
from app.services.po_import import import_po_report
from app.services.sales_velocity_import import import_sales_velocity_report
from app.services.sku_import import import_sku_master

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/sku-master", response_model=ImportSummaryResponse)
async def upload_sku_master(
    file: UploadFile = File(...),
    brand_id: int = Form(...),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    content = await file.read()
    return import_sku_master(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/availability", response_model=ImportSummaryResponse)
async def upload_availability(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_availability_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/sales-velocity", response_model=ImportSummaryResponse)
async def upload_sales_velocity(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_sales_velocity_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/inventory", response_model=ImportSummaryResponse)
async def upload_inventory(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_inventory_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/po", response_model=ImportSummaryResponse)
async def upload_po(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_po_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/dispatch", response_model=ImportSummaryResponse)
async def upload_dispatch(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_dispatch_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)


@router.post("/grn", response_model=ImportSummaryResponse)
async def upload_grn(
    file: UploadFile = File(...),
    brand_id_form: int | None = Form(default=None, alias="brand_id"),
    brand_id_query: int | None = Query(default=None, alias="brand_id"),
    db: Session = Depends(get_db_session),
) -> ImportSummaryResponse:
    brand_id = brand_id_form if brand_id_form is not None else brand_id_query
    if brand_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="brand_id is required")

    content = await file.read()
    return import_grn_report(db=db, brand_id=brand_id, file_name=file.filename or "upload.csv", content=content)
