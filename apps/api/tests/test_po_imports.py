from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand, PORecord, SKU

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


def upload_po(brand_id: int, csv_data: str, filename: str = "po.csv"):
    return client.post(
        "/imports/po",
        files={"file": (filename, csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_po_rows() -> None:
    seed_brand(60)
    seed_skus(60, ["SKU-1", "SKU-2"])

    response = upload_po(
        60,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "SKU-1,Blinkit,Mumbai,PO-1,12,open,2026-04-01\n"
            "SKU-2,Zepto,Delhi,PO-2,8,closed,2026-04-02\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(61)
    seed_skus(61, ["SKU-1"])

    response = upload_po(61, "sku_code,platform,city,po_number,po_qty,po_status\nSKU-1,Blinkit,Mumbai,PO-1,12,open\n")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "po_date" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(62)
    seed_skus(62, ["SKU-1"])

    response = upload_po(
        62,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "UNKNOWN,Blinkit,Mumbai,PO-1,12,open,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,PO-2,8,open,2026-04-02\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_empty_platform_city_create_row_level_error() -> None:
    seed_brand(63)
    seed_skus(63, ["SKU-1"])

    response = upload_po(
        63,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "SKU-1,,Mumbai,PO-1,2,open,2026-04-01\n"
            "SKU-1,Blinkit,,PO-2,2,open,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"platform", "city"}


def test_invalid_po_qty_creates_row_level_error() -> None:
    seed_brand(64)
    seed_skus(64, ["SKU-1"])

    response = upload_po(64, "sku_code,platform,city,po_number,po_qty,po_status,po_date\nSKU-1,Blinkit,Mumbai,PO-1,abc,open,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_numeric"


def test_negative_po_qty_creates_row_level_error() -> None:
    seed_brand(65)
    seed_skus(65, ["SKU-1"])

    response = upload_po(65, "sku_code,platform,city,po_number,po_qty,po_status,po_date\nSKU-1,Blinkit,Mumbai,PO-1,-1,open,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "negative_value"


def test_invalid_po_date_creates_row_level_error() -> None:
    seed_brand(66)
    seed_skus(66, ["SKU-1"])

    response = upload_po(66, "sku_code,platform,city,po_number,po_qty,po_status,po_date\nSKU-1,Blinkit,Mumbai,PO-1,1,open,not-a-date\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_date"


def test_empty_po_number_or_status_create_row_level_error() -> None:
    seed_brand(69)
    seed_skus(69, ["SKU-1"])

    response = upload_po(
        69,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "SKU-1,Blinkit,Mumbai,,1,open,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,PO-2,1,,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"po_number", "po_status"}


def test_duplicate_po_not_inserted_and_counted() -> None:
    seed_brand(67)
    seed_skus(67, ["SKU-1"])

    response = upload_po(
        67,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "SKU-1,Blinkit,Mumbai,PO-1,1,open,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,PO-1,5,closed,2026-04-02\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["duplicate_rows"] == 1

    with TestingSessionLocal() as db:
        count = db.query(PORecord).filter(PORecord.brand_id == 67).count()
        assert count == 1


def test_duplicate_po_scoped_to_source_file() -> None:
    seed_brand(679)
    seed_skus(679, ["SKU-1"])

    csv_data = "sku_code,platform,city,po_number,po_qty,po_status,po_date\nSKU-1,Blinkit,Mumbai,PO-1,1,open,2026-04-01\n"
    first = upload_po(679, csv_data, filename="po_a.csv")
    second = upload_po(679, csv_data, filename="po_b.csv")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["accepted_rows"] == 1
    assert second.json()["accepted_rows"] == 1
    assert second.json()["duplicate_rows"] == 0

    with TestingSessionLocal() as db:
        count = db.query(PORecord).filter(PORecord.brand_id == 679).count()
        assert count == 2


def test_get_po_records_returns_rows_and_supports_filters() -> None:
    seed_brand(68)
    seed_skus(68, ["SKU-1", "SKU-2"])
    upload_po(
        68,
        (
            "sku_code,platform,city,po_number,po_qty,po_status,po_date\n"
            "SKU-1,Blinkit,Mumbai,PO-1,8,open,2026-04-01\n"
            "SKU-2,Zepto,Delhi,PO-2,4,closed,2026-04-02\n"
        ),
    )

    response = client.get(
        "/po-records",
        params={"brand_id": 68, "sku_code": "SKU-1", "platform": "Blinkit", "city": "Mumbai"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
