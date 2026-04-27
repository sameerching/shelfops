from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.schemas.imports import ImportSummaryResponse
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
