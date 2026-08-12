from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api import database
from services.api.main import app


@pytest.fixture
def supplier_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(database, "SUPPLIERS_DB_PATH", tmp_path / "suppliers.json")
    with TestClient(app) as client:
        yield client


def test_context_seed_is_complete_and_idempotent(supplier_client: TestClient) -> None:
    first = supplier_client.get("/suppliers")
    assert first.status_code == 200
    assert len(first.json()) == 15
    assert {supplier["country"] for supplier in first.json()} == {"USA", "UK"}

    second = supplier_client.get("/suppliers")
    assert second.status_code == 200
    assert len(second.json()) == 15


def test_supplier_filters_and_validation(supplier_client: TestClient) -> None:
    usa = supplier_client.get("/suppliers", params={"country": "USA"})
    assert usa.status_code == 200
    assert usa.json()
    assert all(item["country"] == "USA" for item in usa.json())

    laboratory = supplier_client.get("/suppliers", params={"category": "laboratory_services"})
    assert laboratory.status_code == 200
    assert laboratory.json()
    assert all("laboratory_services" in item["categories"] for item in laboratory.json())

    invalid = supplier_client.post(
        "/suppliers",
        json={
            "name": "Invalid Supplier",
            "country": "USA",
            "categories": ["medical_supplies"],
            "monthly_rate": 0,
            "currency": "USD",
            "status": "paused",
        },
    )
    assert invalid.status_code == 422


def test_supplier_creation_returns_server_fields(supplier_client: TestClient) -> None:
    response = supplier_client.post(
        "/suppliers",
        json={
            "name": "New HealthCore Supplier",
            "country": "USA",
            "categories": ["training_platforms"],
            "monthly_rate": 1250,
            "currency": "USD",
            "status": "active",
            "contact_email": "supplier@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] > 15
    assert payload["updated_at"]
    assert payload["name"] == "New HealthCore Supplier"


def test_status_and_delete_endpoints_have_consistent_errors(supplier_client: TestClient) -> None:
    suspended = supplier_client.patch("/suppliers/1/status", json={"status": "suspended"})
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    assert supplier_client.patch("/suppliers/1/status", json={"status": "paused"}).status_code == 422
    assert supplier_client.patch("/suppliers/999/status", json={"status": "active"}).status_code == 404
    assert supplier_client.patch("/suppliers/999/rate", json={"monthly_rate": 100}).status_code == 404

    deleted = supplier_client.delete("/suppliers/1")
    assert deleted.status_code == 200
    assert supplier_client.get("/suppliers/1").status_code == 404
    assert supplier_client.delete("/suppliers/999").status_code == 404


def test_rate_update_records_updated_at_and_missing_supplier_is_404(supplier_client: TestClient) -> None:
    original = supplier_client.get("/suppliers/1").json()
    updated = supplier_client.patch("/suppliers/1/rate", json={"monthly_rate": 4500})
    assert updated.status_code == 200
    assert updated.json()["monthly_rate"] == 4500
    assert updated.json()["updated_at"] != original["updated_at"]

    assert supplier_client.patch("/suppliers/1/rate", json={"monthly_rate": -1}).status_code == 422
    assert supplier_client.get("/suppliers/999").status_code == 404
