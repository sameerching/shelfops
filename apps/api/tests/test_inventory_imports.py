from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand, InventoryPosition, SKU

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


def upload_inventory(brand_id: int, csv_data: str):
    return client.post(
        "/imports/inventory",
        files={"file": ("inventory.csv", csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_inventory_rows() -> None:
    seed_brand(40)
    seed_skus(40, ["SKU-1", "SKU-2"])

    response = upload_inventory(
        40,
        (
            "sku_code,warehouse,city,available_qty,timestamp\n"
            "SKU-1,WH-1,Mumbai,15,2026-04-01T10:00:00Z\n"
            "SKU-2,WH-2,Delhi,3.5,2026-04-01T10:05:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0
    assert payload["duplicate_rows"] == 0


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(41)
    seed_skus(41, ["SKU-1"])

    response = upload_inventory(41, "sku_code,warehouse,city,available_qty\nSKU-1,WH-1,Mumbai,10\n")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "timestamp" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(42)
    seed_skus(42, ["SKU-1"])

    response = upload_inventory(
        42,
        (
            "sku_code,warehouse,city,available_qty,timestamp\n"
            "UNKNOWN,WH-1,Mumbai,10,2026-04-01T10:00:00Z\n"
            "SKU-1,WH-1,Mumbai,11,2026-04-01T11:00:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_empty_warehouse_city_create_row_level_error() -> None:
    seed_brand(43)
    seed_skus(43, ["SKU-1"])

    response = upload_inventory(
        43,
        (
            "sku_code,warehouse,city,available_qty,timestamp\n"
            "SKU-1,,Mumbai,3,2026-04-01T10:00:00Z\n"
            "SKU-1,WH-1,,3,2026-04-01T11:00:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 2
    assert {error["column_name"] for error in payload["errors"]} == {"warehouse", "city"}


def test_invalid_available_qty_creates_row_level_error() -> None:
    seed_brand(44)
    seed_skus(44, ["SKU-1"])

    response = upload_inventory(
        44,
        "sku_code,warehouse,city,available_qty,timestamp\nSKU-1,WH-1,Mumbai,abc,2026-04-01T10:00:00Z\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_numeric"


def test_negative_available_qty_creates_row_level_error() -> None:
    seed_brand(45)
    seed_skus(45, ["SKU-1"])

    response = upload_inventory(
        45,
        "sku_code,warehouse,city,available_qty,timestamp\nSKU-1,WH-1,Mumbai,-1,2026-04-01T10:00:00Z\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "negative_value"


def test_invalid_timestamp_creates_row_level_error() -> None:
    seed_brand(46)
    seed_skus(46, ["SKU-1"])

    response = upload_inventory(
        46,
        "sku_code,warehouse,city,available_qty,timestamp\nSKU-1,WH-1,Mumbai,1,not-a-time\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_timestamp"


def test_duplicate_inventory_snapshot_not_inserted_and_counted() -> None:
    seed_brand(47)
    seed_skus(47, ["SKU-1"])

    response = upload_inventory(
        47,
        (
            "sku_code,warehouse,city,available_qty,timestamp\n"
            "SKU-1,WH-1,Mumbai,1,2026-04-01T10:00:00Z\n"
            "SKU-1,WH-1,Mumbai,2,2026-04-01T10:00:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["duplicate_rows"] == 1

    with TestingSessionLocal() as db:
        count = db.query(InventoryPosition).filter(InventoryPosition.brand_id == 47).count()
        assert count == 1


def test_get_inventory_returns_rows_and_supports_filters() -> None:
    seed_brand(48)
    seed_skus(48, ["SKU-1", "SKU-2"])
    upload_inventory(
        48,
        (
            "sku_code,warehouse,city,available_qty,timestamp\n"
            "SKU-1,WH-1,Mumbai,8,2026-04-01T10:00:00Z\n"
            "SKU-2,WH-2,Delhi,4,2026-04-01T11:00:00Z\n"
        ),
    )

    response = client.get(
        "/inventory",
        params={"brand_id": 48, "sku_code": "SKU-1", "warehouse": "WH-1", "city": "Mumbai"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
    assert rows[0]["warehouse"] == "WH-1"
