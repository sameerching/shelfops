from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.schemas.imports import ImportSummaryResponse
from app.services.availability_import import import_availability_report
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
