from collections.abc import Generator
from decimal import Decimal

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


def seed_skus(brand_id: int, sku_codes: list[str], selling_price: Decimal = Decimal("10"), margin: Decimal = Decimal("2")) -> None:
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
                        selling_price=selling_price,
                        contribution_margin=margin,
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


def upload_sales_velocity(brand_id: int, csv_data: str):
    return client.post(
        "/imports/sales-velocity",
        files={"file": ("sales_velocity.csv", csv_data, "text/csv")},
        data={"brand_id": str(brand_id)},
    )


def generate_cases(brand_id: int):
    return client.post("/cases/generate", json={"brand_id": brand_id})


def test_oos_snapshot_creates_case() -> None:
    seed_brand(100)
    seed_skus(100, ["SKU-1"])
    upload_availability(
        100,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n",
    )

    response = generate_cases(100)

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_cases"] == 1
    assert payload["cases"][0]["status"] == "detected"


def test_multiple_oos_snapshots_update_same_case() -> None:
    seed_brand(101)
    seed_skus(101, ["SKU-1"])
    upload_availability(
        101,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T16:00:00Z\n"
        ),
    )

    first = generate_cases(101)
    second = generate_cases(101)

    assert first.status_code == 200
    assert second.status_code == 200
    list_response = client.get("/cases", params={"brand_id": 101})
    cases = list_response.json()
    assert len(cases) == 1
    assert cases[0]["stockout_duration_hours"] == "6.0000"


def test_latest_in_stock_marks_case_recovered() -> None:
    seed_brand(102)
    seed_skus(102, ["SKU-1"])
    upload_availability(
        102,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,in_stock,2026-04-01T12:00:00Z\n"
        ),
    )

    response = generate_cases(102)

    assert response.status_code == 200
    case = response.json()["cases"][0]
    assert case["status"] == "recovered"
    assert case["recovered_at"] == "2026-04-01T12:00:00"
    assert case["stockout_duration_hours"] == "2.0000"


def test_recovered_case_is_not_recreated_without_new_oos_incident() -> None:
    seed_brand(109)
    seed_skus(109, ["SKU-1"])
    upload_availability(
        109,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,in_stock,2026-04-01T12:00:00Z\n"
        ),
    )

    first = generate_cases(109)
    second = generate_cases(109)

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["generated_cases"] == 0
    cases = client.get("/cases", params={"brand_id": 109}).json()
    assert len(cases) == 1
    assert cases[0]["status"] == "recovered"


def test_new_oos_incident_after_recovery_gets_fresh_detected_at() -> None:
    seed_brand(110)
    seed_skus(110, ["SKU-1"])
    upload_availability(
        110,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,in_stock,2026-04-01T12:00:00Z\n"
        ),
    )
    generate_cases(110)
    upload_availability(
        110,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-02T09:00:00Z\n",
    )

    second_incident = generate_cases(110)

    assert second_incident.status_code == 200
    payload = second_incident.json()
    assert payload["generated_cases"] == 1
    active_case = next(row for row in payload["cases"] if row["status"] in {"detected", "active"})
    assert active_case["detected_at"] == "2026-04-02T09:00:00"


def test_instock_then_oos_between_runs_closes_and_reopens_case() -> None:
    seed_brand(111)
    seed_skus(111, ["SKU-1"])
    upload_availability(
        111,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n",
    )
    first_generation = generate_cases(111)
    assert first_generation.status_code == 200

    upload_availability(
        111,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,in_stock,2026-04-01T12:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T14:00:00Z\n"
        ),
    )
    second_generation = generate_cases(111)

    assert second_generation.status_code == 200
    payload = second_generation.json()
    assert payload["generated_cases"] == 1
    assert payload["recovered_cases"] == 1
    all_cases = client.get("/cases", params={"brand_id": 111}).json()
    assert len(all_cases) == 2
    recovered_case = next(row for row in all_cases if row["status"] == "recovered")
    active_case = next(row for row in all_cases if row["status"] in {"detected", "active"})
    assert recovered_case["detected_at"] == "2026-04-01T10:00:00"
    assert recovered_case["recovered_at"] == "2026-04-01T12:00:00"
    assert active_case["detected_at"] == "2026-04-01T14:00:00"


def test_backfilled_oos_updates_existing_open_case_without_duplicate() -> None:
    seed_brand(112)
    seed_skus(112, ["SKU-1"])
    upload_availability(
        112,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T12:00:00Z\n"
        ),
    )
    first_generation = generate_cases(112)
    assert first_generation.status_code == 200
    assert len(client.get("/cases", params={"brand_id": 112}).json()) == 1

    upload_availability(
        112,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T08:00:00Z\n",
    )
    second_generation = generate_cases(112)

    assert second_generation.status_code == 200
    payload = second_generation.json()
    assert payload["generated_cases"] == 0
    all_cases = client.get("/cases", params={"brand_id": 112}).json()
    assert len(all_cases) == 1
    assert all_cases[0]["detected_at"] == "2026-04-01T08:00:00"
    assert all_cases[0]["stockout_duration_hours"] == "4.0000"


def test_lost_sales_and_margin_calculation_with_velocity_and_sku_values() -> None:
    seed_brand(103)
    seed_skus(103, ["SKU-1"], selling_price=Decimal("100"), margin=Decimal("30"))
    upload_sales_velocity(103, "sku_code,platform,city,avg_units_per_day\nSKU-1,Blinkit,Mumbai,24\n")
    upload_availability(
        103,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T00:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-02T00:00:00Z\n"
        ),
    )

    response = generate_cases(103)

    assert response.status_code == 200
    case = response.json()["cases"][0]
    assert case["estimated_lost_sales"] == "2400.00"
    assert case["estimated_lost_margin"] == "720.00"


def test_missing_sales_velocity_uses_zero_estimates() -> None:
    seed_brand(104)
    seed_skus(104, ["SKU-1"], selling_price=Decimal("100"), margin=Decimal("30"))
    upload_availability(
        104,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n",
    )

    response = generate_cases(104)

    assert response.status_code == 200
    case = response.json()["cases"][0]
    assert case["estimated_lost_sales"] == "0.00"
    assert case["estimated_lost_margin"] == "0.00"


def test_priority_rules_cover_all_bands() -> None:
    seed_brand(105)
    seed_skus(105, ["SKU-P0", "SKU-P1", "SKU-P2", "SKU-P3"], selling_price=Decimal("500"), margin=Decimal("50"))
    upload_sales_velocity(
        105,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-P0,Blinkit,Mumbai,2400\n"
            "SKU-P1,Blinkit,Mumbai,800\n"
            "SKU-P2,Blinkit,Mumbai,200\n"
            "SKU-P3,Blinkit,Mumbai,10\n"
        ),
    )
    upload_availability(
        105,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-P0,Blinkit,Mumbai,L1,oos,2026-04-01T00:00:00Z\n"
            "SKU-P0,Blinkit,Mumbai,L1,oos,2026-04-02T00:00:00Z\n"
            "SKU-P1,Blinkit,Mumbai,L2,oos,2026-04-01T00:00:00Z\n"
            "SKU-P1,Blinkit,Mumbai,L2,oos,2026-04-02T00:00:00Z\n"
            "SKU-P2,Blinkit,Mumbai,L3,oos,2026-04-01T00:00:00Z\n"
            "SKU-P2,Blinkit,Mumbai,L3,oos,2026-04-02T00:00:00Z\n"
            "SKU-P3,Blinkit,Mumbai,L4,oos,2026-04-01T00:00:00Z\n"
            "SKU-P3,Blinkit,Mumbai,L4,oos,2026-04-02T00:00:00Z\n"
        ),
    )

    response = generate_cases(105)

    assert response.status_code == 200
    priorities = {row["sku_code"]: row["priority"] for row in response.json()["cases"]}
    assert priorities["SKU-P0"] == "P0"
    assert priorities["SKU-P1"] == "P1"
    assert priorities["SKU-P2"] == "P2"
    assert priorities["SKU-P3"] == "P3"


def test_get_cases_returns_generated_cases() -> None:
    seed_brand(106)
    seed_skus(106, ["SKU-1"])
    upload_availability(
        106,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n",
    )
    generate_cases(106)

    response = client.get("/cases", params={"brand_id": 106})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"


def test_get_case_detail_returns_case() -> None:
    seed_brand(107)
    seed_skus(107, ["SKU-1"])
    upload_availability(
        107,
        "sku_code,platform,city,location,status,timestamp\nSKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T10:00:00Z\n",
    )
    generate_payload = generate_cases(107).json()
    case_id = generate_payload["cases"][0]["id"]

    response = client.get(f"/cases/{case_id}")

    assert response.status_code == 200
    row = response.json()
    assert row["id"] == case_id
    assert row["platform"] == "Blinkit"


def test_case_filters_work() -> None:
    seed_brand(108)
    seed_skus(108, ["SKU-1", "SKU-2"], selling_price=Decimal("500"), margin=Decimal("50"))
    upload_sales_velocity(
        108,
        (
            "sku_code,platform,city,avg_units_per_day\n"
            "SKU-1,Blinkit,Mumbai,100\n"
            "SKU-2,Zepto,Delhi,10\n"
        ),
    )
    upload_availability(
        108,
        (
            "sku_code,platform,city,location,status,timestamp\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-01T00:00:00Z\n"
            "SKU-1,Blinkit,Mumbai,Andheri,oos,2026-04-02T00:00:00Z\n"
            "SKU-2,Zepto,Delhi,Saket,oos,2026-04-01T00:00:00Z\n"
            "SKU-2,Zepto,Delhi,Saket,in_stock,2026-04-01T01:00:00Z\n"
        ),
    )
    generate_cases(108)

    response = client.get(
        "/cases",
        params={
            "brand_id": 108,
            "platform": "Blinkit",
            "city": "Mumbai",
            "status": "active",
            "priority": "P1",
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-1"
