"""Read-only tools for live HealthCore operational data."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field


TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "4.0"))


class TicketLookupInput(BaseModel):
    ticket_id: int | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, min_length=1, max_length=64)


class TicketLookupOutput(BaseModel):
    found: bool
    ticket_id: int | None = None
    status: str | None = None
    category: str | None = None
    source: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    error: str | None = None
    outcome: str = "success"


class InventoryLookupInput(BaseModel):
    product_id: int | None = Field(default=None, gt=0)
    search: str | None = Field(default=None, min_length=1, max_length=200)


class InventoryProduct(BaseModel):
    id: int
    name: str
    sku: str
    current_stock: int


class InventoryLookupOutput(BaseModel):
    found: bool
    products: list[InventoryProduct] = Field(default_factory=list)
    error: str | None = None
    outcome: str = "success"


def lookup_ticket(request: TicketLookupInput) -> TicketLookupOutput:
    """Read one incident or a status-filtered incident list from the API."""

    base_url = os.getenv("INCIDENTS_API_BASE_URL", "http://localhost:8000").rstrip("/")
    path = f"/api/incidents/{request.ticket_id}" if request.ticket_id is not None else "/api/incidents"
    params = {"status": request.status} if request.ticket_id is None and request.status else None
    try:
        response = httpx.get(
            f"{base_url}{path}",
            params=params,
            headers=_service_headers(),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return TicketLookupOutput(found=False, error="timeout", outcome="timeout")
    except httpx.HTTPError:
        return TicketLookupOutput(
            found=False,
            error="incident_service_unavailable",
            outcome="http_error",
        )

    if response.status_code == 404:
        return TicketLookupOutput(found=False, error="ticket_not_found", outcome="not_found")
    if response.is_error:
        return TicketLookupOutput(
            found=False,
            error=f"incident_service_http_{response.status_code}",
            outcome="http_error",
        )

    try:
        payload: Any = response.json()
    except ValueError:
        return TicketLookupOutput(
            found=False,
            error="invalid_incident_response",
            outcome="http_error",
        )

    if isinstance(payload, list):
        if not payload:
            return TicketLookupOutput(found=False, error="ticket_not_found", outcome="not_found")
        payload = payload[0]
    if not isinstance(payload, dict) or "id" not in payload:
        return TicketLookupOutput(
            found=False,
            error="invalid_incident_response",
            outcome="http_error",
        )

    return TicketLookupOutput(
        found=True,
        ticket_id=int(payload["id"]),
        status=_optional_string(payload.get("status")),
        category=_optional_string(payload.get("category")),
        source=_optional_string(payload.get("origin")),
        created_at=_optional_string(payload.get("created_at")),
        updated_at=_optional_string(payload.get("updated_at")),
    )


def lookup_inventory(request: InventoryLookupInput) -> InventoryLookupOutput:
    """Read current stock from the existing inventory API, never a local copy."""

    base_url = os.getenv("INVENTORY_API_BASE_URL", "http://localhost:8000").rstrip("/")
    path = (
        f"/inventory/products/{request.product_id}"
        if request.product_id is not None
        else "/inventory/products"
    )
    try:
        response = httpx.get(
            f"{base_url}{path}",
            headers=_service_headers(),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return InventoryLookupOutput(found=False, error="timeout", outcome="timeout")
    except httpx.HTTPError:
        return InventoryLookupOutput(
            found=False,
            error="inventory_service_unavailable",
            outcome="http_error",
        )

    if response.status_code == 404:
        return InventoryLookupOutput(found=False, error="product_not_found", outcome="not_found")
    if response.is_error:
        return InventoryLookupOutput(
            found=False,
            error=f"inventory_service_http_{response.status_code}",
            outcome="http_error",
        )

    try:
        payload: Any = response.json()
        rows = [payload] if isinstance(payload, dict) else payload
        products = [InventoryProduct.model_validate(row) for row in rows]
    except (TypeError, ValueError):
        return InventoryLookupOutput(
            found=False,
            error="invalid_inventory_response",
            outcome="http_error",
        )

    if request.search:
        needle = request.search.casefold()
        products = [
            product
            for product in products
            if needle in product.name.casefold() or needle in product.sku.casefold()
        ]
    if not products:
        return InventoryLookupOutput(found=False, error="product_not_found", outcome="not_found")
    return InventoryLookupOutput(found=True, products=products)


def _service_headers() -> dict[str, str]:
    token = os.getenv("AGENT_SERVICE_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
