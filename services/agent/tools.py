"""Compatibility contracts backed by the HealthCore MCP server."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .mcp_client import call_mcp_tool


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
    incidents: list[dict[str, Any]] = Field(default_factory=list)
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
    """Look up a ticket through the MCP server, never the incident API directly."""

    arguments: dict[str, Any] = {"action": "get_status"}
    if request.ticket_id is not None:
        arguments["ticket_id"] = request.ticket_id
    elif request.status:
        arguments["status"] = request.status
    raw = call_mcp_tool("manage_incident_ticket", arguments)
    if not raw.get("ok"):
        error_code = str(raw.get("error_code", "MCP_TOOL_ERROR"))
        outcome = "not_found" if error_code == "UPSTREAM_NOT_FOUND" else "http_error"
        return TicketLookupOutput(found=False, error=error_code, outcome=outcome)
    payload = raw.get("incident")
    if payload is None and isinstance(raw.get("incidents"), list):
        incidents = raw["incidents"]
        return TicketLookupOutput(
            found=bool(incidents),
            status=request.status,
            incidents=incidents,
            error=None if incidents else "ticket_not_found",
            outcome="success" if incidents else "not_found",
        )
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, dict) or "id" not in payload:
        return TicketLookupOutput(found=False, error="invalid_mcp_response", outcome="http_error")
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
    """Read current stock through the MCP server, never a local copy."""

    arguments: dict[str, Any] = {"action": "query"}
    if request.product_id is not None:
        arguments["product_id"] = request.product_id
    if request.search:
        arguments["search"] = request.search
    raw = call_mcp_tool("query_inventory", arguments)
    if not raw.get("ok"):
        error_code = str(raw.get("error_code", "MCP_TOOL_ERROR"))
        outcome = "not_found" if error_code == "UPSTREAM_NOT_FOUND" else "http_error"
        return InventoryLookupOutput(found=False, error=error_code, outcome=outcome)
    try:
        products = [InventoryProduct.model_validate(row) for row in raw.get("products", [])]
    except (TypeError, ValueError):
        return InventoryLookupOutput(found=False, error="invalid_mcp_response", outcome="http_error")
    return InventoryLookupOutput(found=bool(products), products=products)


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
