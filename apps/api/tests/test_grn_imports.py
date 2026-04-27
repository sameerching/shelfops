from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand, GRNRecord, SKU

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
Base.metadata.create_all(bind=engine)


def override_get_db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db_session] = override_get_db_session
client = TestClient(app)


def seed_brand(brand_id: int) -> None:
    with TestingSessionLocal() as db:
        if db.get(Brand, brand_id) is None:
            db.add(Brand(id=brand_id, name=f"Brand {brand_id}", category="FMCG"))
            db.commit()


def seed_skus(brand_id: int, sku_codes: list[str]) -> None:
    with TestingSessionLocal() as db:
        for idx, code in enumerate(sku_codes, start=1):
            exists = db.query(SKU).filter(SKU.brand_id == brand_id, SKU.sku_code == code).first()
            if exists is None:
                db.add(
                    SKU(
                        brand_id=brand_id,
                        sku_code=code,
                        sku_name=f"Item {idx}",
                        category="Snacks",
                        selling_price=10,
                        contribution_margin=0.2,
                        case_pack=6,
                    )
                )
        db.commit()


def upload_grn(brand_id: int, csv_data: str):
    return client.post(
        "/imports/grn",
        files={"file": ("grn.csv", csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_grn_rows() -> None:
    seed_brand(80)
    seed_skus(80, ["SKU-1", "SKU-2"])

    response = upload_grn(
        80,
        (
            "sku_code,platform,city,grn_qty,grn_status,grn_date\n"
            "SKU-1,Blinkit,Mumbai,12,received,2026-04-01\n"
            "SKU-2,Zepto,Delhi,8,received,2026-04-02\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(81)
    seed_skus(81, ["SKU-1"])

    response = upload_grn(81, "sku_code,platform,city,grn_qty,grn_status\nSKU-1,Blinkit,Mumbai,12,received\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "grn_date" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(82)
    seed_skus(82, ["SKU-1"])

    response = upload_grn(
        82,
        (
            "sku_code,platform,city,grn_qty,grn_status,grn_date\n"
            "UNKNOWN,Blinkit,Mumbai,12,received,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,8,received,2026-04-02\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_empty_platform_city_create_row_level_error() -> None:
    seed_brand(83)
    seed_skus(83, ["SKU-1"])

    response = upload_grn(
        83,
        (
            "sku_code,platform,city,grn_qty,grn_status,grn_date\n"
            "SKU-1,,Mumbai,2,received,2026-04-01\n"
            "SKU-1,Blinkit,,2,received,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"platform", "city"}


def test_invalid_grn_qty_creates_row_level_error() -> None:
    seed_brand(84)
    seed_skus(84, ["SKU-1"])

    response = upload_grn(84, "sku_code,platform,city,grn_qty,grn_status,grn_date\nSKU-1,Blinkit,Mumbai,abc,received,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_numeric"


def test_negative_grn_qty_creates_row_level_error() -> None:
    seed_brand(85)
    seed_skus(85, ["SKU-1"])

    response = upload_grn(85, "sku_code,platform,city,grn_qty,grn_status,grn_date\nSKU-1,Blinkit,Mumbai,-1,received,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "negative_value"


def test_invalid_grn_date_creates_row_level_error() -> None:
    seed_brand(86)
    seed_skus(86, ["SKU-1"])

    response = upload_grn(86, "sku_code,platform,city,grn_qty,grn_status,grn_date\nSKU-1,Blinkit,Mumbai,1,received,not-a-date\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_date"


def test_duplicate_grn_not_inserted_and_counted() -> None:
    seed_brand(87)
    seed_skus(87, ["SKU-1"])

    response = upload_grn(
        87,
        (
            "sku_code,platform,city,grn_qty,grn_status,grn_date\n"
            "SKU-1,Blinkit,Mumbai,1,received,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,5,closed,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["duplicate_rows"] == 1

    with TestingSessionLocal() as db:
        count = db.query(GRNRecord).filter(GRNRecord.brand_id == 87).count()
        assert count == 1


def test_get_grn_records_returns_rows_and_supports_filters() -> None:
    seed_brand(88)
    seed_skus(88, ["SKU-1", "SKU-2"])
    upload_grn(
        88,
        (
            "sku_code,platform,city,grn_qty,grn_status,grn_date\n"
            "SKU-1,Blinkit,Mumbai,8,received,2026-04-01\n"
            "SKU-2,Zepto,Delhi,4,received,2026-04-02\n"
        ),
    )

    response = client.get(
        "/grn-records",
        params={"brand_id": 88, "sku_code": "SKU-1", "platform": "Blinkit", "city": "Mumbai"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
