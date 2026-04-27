from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand, SKU

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


def upload_sales_velocity(brand_id: int, csv_data: str):
    return client.post(
        "/imports/sales-velocity",
        files={"file": ("sales_velocity.csv", csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_sales_velocity_rows() -> None:
    seed_brand(30)
    seed_skus(30, ["SKU-1", "SKU-2"])

    response = upload_sales_velocity(
        30,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-1,Blinkit,Mumbai,8.5\n"
            "SKU-2,Zepto,Delhi,4\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0

    list_response = client.get("/sales-velocity", params={"brand_id": 30})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 2


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(31)
    seed_skus(31, ["SKU-1"])

    response = upload_sales_velocity(31, "sku_code,platform,city\nSKU-1,Blinkit,Mumbai\n")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "avg_units_per_day" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(32)
    seed_skus(32, ["SKU-1"])

    response = upload_sales_velocity(
        32,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "UNKNOWN,Blinkit,Mumbai,3\n"
            "SKU-1,Blinkit,Mumbai,2\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_empty_platform_city_create_row_level_error() -> None:
    seed_brand(33)
    seed_skus(33, ["SKU-1"])

    response = upload_sales_velocity(
        33,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-1,,Mumbai,3\n"
            "SKU-1,Blinkit,,3\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"platform", "city"}


def test_invalid_avg_units_per_day_creates_row_level_error() -> None:
    seed_brand(34)
    seed_skus(34, ["SKU-1"])

    response = upload_sales_velocity(
        34,
        "sku_code,platform,city,avg_units_per_day\nSKU-1,Blinkit,Mumbai,abc\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_numeric"


def test_negative_avg_units_per_day_creates_row_level_error() -> None:
    seed_brand(35)
    seed_skus(35, ["SKU-1"])

    response = upload_sales_velocity(
        35,
        "sku_code,platform,city,avg_units_per_day\nSKU-1,Blinkit,Mumbai,-1\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "negative_value"


def test_duplicate_brand_sku_platform_city_upserts_and_counts_duplicates() -> None:
    seed_brand(36)
    seed_skus(36, ["SKU-1"])

    first = upload_sales_velocity(36, "sku_code,platform,city,avg_units_per_day\nSKU-1,Blinkit,Mumbai,2\n")
    assert first.status_code == 200

    second = upload_sales_velocity(
        36,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-1,Blinkit,Mumbai,5\n"
            "SKU-1,Blinkit,Mumbai,7\n"
        ),
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["accepted_rows"] == 2
    assert payload["duplicate_rows"] == 2

    list_response = client.get("/sales-velocity", params={"brand_id": 36})
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["avg_units_per_day"] == "7.0000"


def test_get_sales_velocity_supports_filters() -> None:
    seed_brand(37)
    seed_skus(37, ["SKU-1", "SKU-2"])
    upload_sales_velocity(
        37,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-1,Blinkit,Mumbai,8\n"
            "SKU-2,Zepto,Delhi,4\n"
        ),
    )

    response = client.get(
        "/sales-velocity",
        params={"brand_id": 37, "sku_code": "SKU-1", "platform": "Blinkit", "city": "Mumbai"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
