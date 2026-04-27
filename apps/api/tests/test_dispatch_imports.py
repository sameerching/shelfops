from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand, DispatchRecord, SKU

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


def upload_dispatch(brand_id: int, csv_data: str, filename: str = "dispatch.csv"):
    return client.post(
        "/imports/dispatch",
        files={"file": (filename, csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_dispatch_rows() -> None:
    seed_brand(70)
    seed_skus(70, ["SKU-1", "SKU-2"])

    response = upload_dispatch(
        70,
        (
            "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
            "SKU-1,Blinkit,Mumbai,12,open,2026-04-01\n"
            "SKU-2,Zepto,Delhi,8,closed,2026-04-02\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(71)
    seed_skus(71, ["SKU-1"])

    response = upload_dispatch(71, "sku_code,platform,city,dispatch_qty,dispatch_status\nSKU-1,Blinkit,Mumbai,12,open\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "dispatch_date" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(72)
    seed_skus(72, ["SKU-1"])

    response = upload_dispatch(
        72,
        (
            "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
            "UNKNOWN,Blinkit,Mumbai,12,open,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,8,open,2026-04-02\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_empty_platform_city_create_row_level_error() -> None:
    seed_brand(73)
    seed_skus(73, ["SKU-1"])

    response = upload_dispatch(
        73,
        (
            "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
            "SKU-1,,Mumbai,2,open,2026-04-01\n"
            "SKU-1,Blinkit,,2,open,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"platform", "city"}


def test_invalid_dispatch_qty_creates_row_level_error() -> None:
    seed_brand(74)
    seed_skus(74, ["SKU-1"])

    response = upload_dispatch(74, "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\nSKU-1,Blinkit,Mumbai,abc,open,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_numeric"


def test_negative_dispatch_qty_creates_row_level_error() -> None:
    seed_brand(75)
    seed_skus(75, ["SKU-1"])

    response = upload_dispatch(75, "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\nSKU-1,Blinkit,Mumbai,-1,open,2026-04-01\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "negative_value"


def test_invalid_dispatch_date_creates_row_level_error() -> None:
    seed_brand(76)
    seed_skus(76, ["SKU-1"])

    response = upload_dispatch(76, "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\nSKU-1,Blinkit,Mumbai,1,open,not-a-date\n")

    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_date"


def test_duplicate_dispatch_not_inserted_and_counted() -> None:
    seed_brand(77)
    seed_skus(77, ["SKU-1"])

    response = upload_dispatch(
        77,
        (
            "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
            "SKU-1,Blinkit,Mumbai,1,open,2026-04-01\n"
            "SKU-1,Blinkit,Mumbai,5,closed,2026-04-01\n"
        ),
    )

    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["duplicate_rows"] == 1

    with TestingSessionLocal() as db:
        count = db.query(DispatchRecord).filter(DispatchRecord.brand_id == 77).count()
        assert count == 1


def test_duplicate_dispatch_scoped_to_source_file() -> None:
    seed_brand(779)
    seed_skus(779, ["SKU-1"])

    csv_data = (
        "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
        "SKU-1,Blinkit,Mumbai,1,open,2026-04-01\n"
    )
    first = upload_dispatch(779, csv_data, filename="dispatch_a.csv")
    second = upload_dispatch(779, csv_data, filename="dispatch_b.csv")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["accepted_rows"] == 1
    assert second.json()["accepted_rows"] == 1
    assert second.json()["duplicate_rows"] == 0

    with TestingSessionLocal() as db:
        count = db.query(DispatchRecord).filter(DispatchRecord.brand_id == 779).count()
        assert count == 2


def test_get_dispatch_records_returns_rows_and_supports_filters() -> None:
    seed_brand(78)
    seed_skus(78, ["SKU-1", "SKU-2"])
    upload_dispatch(
        78,
        (
            "sku_code,platform,city,dispatch_qty,dispatch_status,dispatch_date\n"
            "SKU-1,Blinkit,Mumbai,8,open,2026-04-01\n"
            "SKU-2,Zepto,Delhi,4,closed,2026-04-02\n"
        ),
    )

    response = client.get(
        "/dispatch-records",
        params={"brand_id": 78, "sku_code": "SKU-1", "platform": "Blinkit", "city": "Mumbai"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
