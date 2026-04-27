from collections.abc import Generator
from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.main import app
from app.models import entities  # noqa: F401
from app.models.entities import Brand

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


def seed_brand(brand_id: int = 1) -> None:
    with TestingSessionLocal() as db:
        if db.get(Brand, brand_id) is None:
            db.add(Brand(id=brand_id, name=f"Brand {brand_id}", category="FMCG"))
            db.commit()


def test_valid_csv_upload_creates_skus() -> None:
    seed_brand(1)
    csv_data = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack\n"
        "SKU-1,Item 1,Snacks,10.5,0.22,6\n"
        "SKU-2,Item 2,Snacks,20,0.30,12\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0
    assert payload["errors"] == []

    list_response = client.get("/skus", params={"brand_id": 1})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2


def test_missing_required_column_hard_fails_batch() -> None:
    seed_brand(2)
    csv_data = (
        "sku_code,sku_name,category,selling_price,case_pack\n"
        "SKU-1,Item 1,Snacks,10.5,6\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "2"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 0
    assert payload["rejected_rows"] == 1
    assert any(err["column_name"] == "contribution_margin" for err in payload["errors"])


def test_invalid_numeric_value_creates_row_error_and_continues() -> None:
    seed_brand(3)
    csv_data = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack\n"
        "SKU-1,Item 1,Snacks,abc,0.22,6\n"
        "SKU-2,Item 2,Snacks,20,0.30,12\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["column_name"] == "selling_price"

    list_response = client.get("/skus", params={"brand_id": 3})
    assert len(list_response.json()) == 1


def test_blank_required_text_field_is_rejected() -> None:
    seed_brand(6)
    csv_data = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack\n"
        "SKU-1,,Snacks,10,0.2,6\n"
        "SKU-2,Item 2,Snacks,12,0.25,6\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "6"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 1
    assert payload["errors"][0]["column_name"] == "sku_name"


def test_duplicate_sku_code_in_same_upload_upserts() -> None:
    seed_brand(4)
    csv_data = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack\n"
        "SKU-1,Item 1,Snacks,10,0.2,6\n"
        "SKU-1,Item 1 Updated,Snacks,15,0.25,6\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rows"] == 2
    assert payload["duplicate_rows"] >= 1

    list_response = client.get("/skus", params={"brand_id": 4})
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["sku_name"] == "Item 1 Updated"


def test_numeric_sku_code_preserves_leading_zeroes() -> None:
    seed_brand(7)
    csv_data = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack\n"
        "00123,Item 123,Snacks,10,0.2,6\n"
    )

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", csv_data, "text/csv")},
        data={"brand_id": "7"},
    )

    assert response.status_code == 200
    list_response = client.get("/skus", params={"brand_id": 7})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "00123"


def test_invalid_boolean_does_not_mutate_existing_duplicate() -> None:
    seed_brand(8)
    initial_csv = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack,is_hero_sku\n"
        "SKU-1,Original Name,Snacks,10,0.2,6,false\n"
    )
    update_csv = (
        "sku_code,sku_name,category,selling_price,contribution_margin,case_pack,is_hero_sku\n"
        "SKU-1,Mutated Name,Snacks,15,0.3,6,not-a-bool\n"
    )

    initial_response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", initial_csv, "text/csv")},
        data={"brand_id": "8"},
    )
    assert initial_response.status_code == 200
    assert initial_response.json()["rejected_rows"] == 0

    update_response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.csv", update_csv, "text/csv")},
        data={"brand_id": "8"},
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["accepted_rows"] == 0
    assert update_payload["rejected_rows"] == 1

    list_response = client.get("/skus", params={"brand_id": 8})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["sku_name"] == "Original Name"
    assert rows[0]["selling_price"] == "10"
    assert rows[0]["is_hero_sku"] is False


def test_get_skus_returns_uploaded_skus() -> None:
    seed_brand(5)
    data = pd.DataFrame(
        [
            {
                "sku_code": "SKU-10",
                "sku_name": "Item 10",
                "category": "Beverages",
                "selling_price": 30,
                "contribution_margin": 0.4,
                "case_pack": 24,
            }
        ]
    )
    buf = BytesIO()
    data.to_excel(buf, index=False)
    buf.seek(0)

    response = client.post(
        "/imports/sku-master",
        files={"file": ("sku_master.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"brand_id": "5"},
    )

    assert response.status_code == 200
    list_response = client.get("/skus", params={"brand_id": 5})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["sku_code"] == "SKU-10"
