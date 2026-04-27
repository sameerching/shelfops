from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.schemas.cases import CaseGenerateRequest, CaseGenerateResponse, StockoutCaseResponse
from app.services.case_engine import generate_stockout_cases, get_case_detail, list_cases

router = APIRouter(tags=["cases"])


@router.post("/cases/generate", response_model=CaseGenerateResponse)
def generate_cases(
    payload: CaseGenerateRequest | None = None,
    brand_id: int | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> CaseGenerateResponse:
    effective_brand_id = payload.brand_id if payload is not None else brand_id
    if effective_brand_id is None:
        raise HTTPException(status_code=422, detail="brand_id is required in body or query")

    generated, updated, recovered, _ = generate_stockout_cases(db, effective_brand_id)
    responses = list_cases(db, brand_id=effective_brand_id)
    return CaseGenerateResponse(
        generated_cases=generated,
        updated_cases=updated,
        recovered_cases=recovered,
        cases=responses,
    )


@router.get("/cases", response_model=list[StockoutCaseResponse])
def get_cases(
    brand_id: int = Query(...),
    sku_code: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> list[StockoutCaseResponse]:
    return list_cases(
        db,
        brand_id=brand_id,
        sku_code=sku_code,
        platform=platform,
        city=city,
        status=status,
        priority=priority,
    )


@router.get("/cases/{case_id}", response_model=StockoutCaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db_session)) -> StockoutCaseResponse:
    case_detail = get_case_detail(db, case_id)
    if case_detail is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_detail
