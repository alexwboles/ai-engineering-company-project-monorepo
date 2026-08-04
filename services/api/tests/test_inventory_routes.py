from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from services.api.auth_security import get_current_user
from services.api.database import get_db
from services.api.main import app


@pytest.fixture
def inventory_client(user_factory) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: user_factory(user_id=42)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_inventory_schema_has_foreign_keys_and_no_stock_column() -> None:
    from services.api.models import InboundOrder, OutboundOrder, Product

    assert "stock" not in Product.__table__.columns
    assert {str(key.column) for key in InboundOrder.__table__.c.product_id.foreign_keys} == {"products.id"}
    assert {str(key.column) for key in OutboundOrder.__table__.c.product_id.foreign_keys} == {"products.id"}


def test_inventory_flow_computes_stock_and_persists_authenticated_user(inventory_client: TestClient) -> None:
    product_response = inventory_client.post(
        "/inventory/products",
        json={"name": "Surgical Gloves", "sku": "HC-GLOVE-001"},
    )
    assert product_response.status_code == 201
    assert product_response.json()["current_stock"] == 0
    product_id = product_response.json()["id"]

    inbound_response = inventory_client.post(
        "/inventory/orders/inbound",
        json={"product_id": product_id, "quantity": 10},
    )
    assert inbound_response.status_code == 201
    assert inbound_response.json()["user_uuid"] == "42"

    outbound_response = inventory_client.post(
        "/inventory/orders/outbound",
        json={"product_id": product_id, "quantity": 4},
    )
    assert outbound_response.status_code == 201
    assert outbound_response.json()["user_uuid"] == "42"

    current_response = inventory_client.get(f"/inventory/products/{product_id}")
    assert current_response.status_code == 200
    assert current_response.json()["current_stock"] == 6

    orders_response = inventory_client.get("/inventory/orders")
    assert orders_response.status_code == 200
    assert len(orders_response.json()) == 2
    assert {order["product"]["sku"] for order in orders_response.json()} == {"HC-GLOVE-001"}


def test_outbound_order_rejects_negative_stock_before_persisting(inventory_client: TestClient) -> None:
    product_id = inventory_client.post(
        "/inventory/products",
        json={"name": "Diagnostic Kit", "sku": "HC-KIT-001"},
    ).json()["id"]
    inventory_client.post(
        "/inventory/orders/inbound",
        json={"product_id": product_id, "quantity": 2},
    )

    response = inventory_client.post(
        "/inventory/orders/outbound",
        json={"product_id": product_id, "quantity": 3},
    )

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]
    assert inventory_client.get(f"/inventory/products/{product_id}").json()["current_stock"] == 2
    assert len(inventory_client.get("/inventory/orders").json()) == 1


def test_inventory_rejects_direct_stock_input(inventory_client: TestClient) -> None:
    response = inventory_client.post(
        "/inventory/products",
        json={"name": "Exam Table", "sku": "HC-TABLE-001", "stock": 99},
    )

    assert response.status_code == 422
