from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import AvailabilitySnapshot, Brand, SKU

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


def upload_availability(brand_id: int, csv_data: str):
    return client.post(
        "/imports/availability",
        files={"file": ("availability.csv", csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def test_valid_csv_upload_creates_availability_snapshots() -> None:
    seed_brand(20)
    seed_skus(20, ["SKU-1", "SKU-2"])

    response = upload_availability(
        20,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,OOS,2026-04-01T10:00:00Z\n"
            "SKU-2,Blinkit,Mumbai,Bandra,available,2026-04-01T10:05:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0
    assert payload["duplicate_rows"] == 0

    list_response = client.get("/availability", params={"brand_id": 20})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"in_stock", "out_of_stock"}


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(21)
    seed_skus(21, ["SKU-1"])

    response = upload_availability(
        21,
        "sku_code,platform,city,location,status\nSKU-1,Blinkit,Mumbai,Andheri,OOS\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "timestamp" for err in payload["errors"])


def test_unknown_sku_code_creates_row_error_and_imports_other_rows() -> None:
    seed_brand(22)
    seed_skus(22, ["SKU-1"])

    response = upload_availability(
        22,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "UNKNOWN,Blinkit,Mumbai,Andheri,OOS,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,in stock,2026-04-01T11:00:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "unknown_sku_code"


def test_invalid_status_creates_row_level_error() -> None:
    seed_brand(23)
    seed_skus(23, ["SKU-1"])

    response = upload_availability(
        23,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,maybe,2026-04-01T10:00:00Z\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_status"


def test_invalid_timestamp_creates_row_level_error() -> None:
    seed_brand(24)
    seed_skus(24, ["SKU-1"])

    response = upload_availability(
        24,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,not-a-time\n",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["error_code"] == "invalid_timestamp"


def test_duplicate_snapshot_not_inserted_and_counted() -> None:
    seed_brand(25)
    seed_skus(25, ["SKU-1"])

    response = upload_availability(
        25,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,out of stock,2026-04-01T10:00:00Z\n"
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["duplicate_rows"] == 1

    with TestingSessionLocal() as db:
        count = db.query(AvailabilitySnapshot).filter(AvailabilitySnapshot.brand_id == 25).count()
        assert count == 1


def test_get_availability_returns_snapshots_with_filters() -> None:
    seed_brand(26)
    seed_skus(26, ["SKU-1", "SKU-2"])
    upload_availability(
        26,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-2,Zepto,Delhi,Saket,in stock,2026-04-01T11:00:00Z\n"
        ),
    )

    response = client.get(
        "/availability",
        params={"brand_id": 26, "platform": "Blinkit", "city": "Mumbai", "status": "out_of_stock"},
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
    assert rows[0]["location"]["platform"] == "Blinkit"
