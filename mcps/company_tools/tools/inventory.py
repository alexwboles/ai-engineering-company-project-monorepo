"""Read-only MCP tool for the real HealthCore inventory API."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from fastmcp.exceptions import ToolError
from pydantic import Field

from ..http import UpstreamError, request_upstream
from .common import instrument, require_tool_scope


INVENTORY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "description": "Whether the read succeeded."},
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "sku": {"type": "string"},
                    "current_stock": {"type": "integer"},
                },
                "required": ["id", "name", "sku", "current_stock"],
            },
        },
        "error_code": {"type": ["string", "null"]},
        "message": {"type": ["string", "null"]},
    },
    "required": ["ok"],
}


def _base_url() -> str:
    return os.getenv("INVENTORY_API_BASE_URL", "http://localhost:8000").rstrip("/")


@instrument("query_inventory")
def query_inventory(
    action: Annotated[Literal["query", "update"], Field(description="Only query is permitted; update is rejected explicitly.")] = "query",
    product_id: Annotated[int | None, Field(default=None, gt=0, description="Product ID to query.")] = None,
    search: Annotated[str | None, Field(default=None, description="Case-insensitive product name or SKU filter.")] = None,
    quantity: Annotated[int | None, Field(default=None, description="Write-only field; any write attempt is rejected.")] = None,
) -> dict[str, Any]:
    """Read current product stock; inventory writes are explicitly forbidden.

    Requires inventory:read. The action=update shape is intentionally accepted
    so an MCP client receives a controlled INVENTORY_WRITE_FORBIDDEN error.
    """

    require_tool_scope("inventory:read")
    if action != "query" or quantity is not None:
        raise ToolError(
            "INVENTORY_WRITE_FORBIDDEN: Inventory tool is read-only. "
            "Write operations are not permitted on this MCP server."
        )
    path = (
        f"{_base_url()}/inventory/products/{product_id}"
        if product_id is not None
        else f"{_base_url()}/inventory/products"
    )
    try:
        payload = request_upstream("GET", path)
    except UpstreamError as exc:
        return {"ok": False, "error_code": exc.error_code, "message": exc.message}
    rows = [payload] if isinstance(payload, dict) else payload
    if search:
        needle = search.casefold()
        rows = [
            row
            for row in rows
            if needle in str(row.get("name", "")).casefold()
            or needle in str(row.get("sku", "")).casefold()
        ]
    if not rows:
        return {
            "ok": False,
            "error_code": "UPSTREAM_NOT_FOUND",
            "message": "No matching HealthCore inventory product was found.",
        }
    return {"ok": True, "products": rows}
