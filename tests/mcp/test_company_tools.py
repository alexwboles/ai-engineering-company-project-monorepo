from __future__ import annotations

import asyncio
import importlib

import jwt
import pytest
from fastapi.testclient import TestClient
from fastmcp.exceptions import ToolError
from mcpauth import AuthInfo

from mcps.company_tools import auth
from mcps.company_tools.server import mcp
from mcps.company_tools.tools.incidents import manage_incident_ticket
from mcps.company_tools.tools.inventory import query_inventory


def _authenticated(scopes: list[str]) -> object:
    return auth.MCP_AUTH._context_var.set(
        AuthInfo(
            token="test-token",
            issuer="http://localhost:8001",
            client_id="test-client",
            subject="test-subject",
            scopes=scopes,
            claims={},
        )
    )


def test_discovery_exposes_descriptive_tools_and_schemas() -> None:
    discovered = asyncio.run(mcp.list_tools())
    by_name = {tool.name: tool for tool in discovered}

    assert {"manage_incident_ticket", "query_inventory"} <= by_name.keys()
    incident_description = (by_name["manage_incident_ticket"].description or "").lower()
    inventory_description = (by_name["query_inventory"].description or "").lower()
    assert "create, update, or check" in incident_description
    assert "read current product stock" in inventory_description
    assert "action" in by_name["manage_incident_ticket"].parameters["properties"]
    assert "action" in by_name["query_inventory"].parameters["properties"]
    assert "incident" in by_name["manage_incident_ticket"].output_schema["properties"]
    assert "products" in by_name["query_inventory"].output_schema["properties"]


def test_mcp_mount_rejects_missing_bearer_token() -> None:
    client = TestClient(importlib.import_module("mcps.company_tools.server").app)
    metadata = client.get("/.well-known/oauth-protected-resource")
    response = client.get("/mcp")

    assert metadata.status_code == 200
    assert metadata.json()["authorization_servers"] == ["http://localhost:8001"]
    assert response.status_code == 401
    assert "token" in response.text.lower()


def test_incident_tool_uses_healthcore_lifecycle_paths(monkeypatch) -> None:
    token = _authenticated(["incidents:read", "incidents:write"])
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, url, *, json=None, params=None):
        calls.append((method, url, json))
        return {"id": 482, "status": json["status"] if json else "open"}

    monkeypatch.setattr("mcps.company_tools.tools.incidents.request_upstream", fake_request)
    try:
        created = manage_incident_ticket(
            action="create",
            title="Printer outage",
            description="The clinic printer is unavailable.",
            category="technical",
            status="open",
            origin="internal",
            branch="technology",
        )
        updated = manage_incident_ticket(action="update", ticket_id=482, status="in_progress")
        looked_up = manage_incident_ticket(action="get_status", ticket_id=482)
        filtered = manage_incident_ticket(action="get_status", status="open")
    finally:
        auth.MCP_AUTH._context_var.reset(token)

    assert created["ok"] is True
    assert updated["ok"] is True
    assert looked_up["ok"] is True
    assert filtered["ok"] is True
    assert calls[0][0:2] == ("POST", "http://localhost:8000/api/incidents")
    assert calls[1][0:2] == ("PATCH", "http://localhost:8000/api/incidents/482/status")
    assert calls[2][0:2] == ("GET", "http://localhost:8000/api/incidents/482")
    assert calls[3][0:2] == ("GET", "http://localhost:8000/api/incidents")


def test_inventory_write_is_explicitly_rejected() -> None:
    token = _authenticated(["inventory:read"])
    try:
        with pytest.raises(ToolError, match="INVENTORY_WRITE_FORBIDDEN"):
            query_inventory(action="update", product_id=7, quantity=2)
    finally:
        auth.MCP_AUTH._context_var.reset(token)


def test_valid_token_reaches_mcp_mount(monkeypatch) -> None:
    monkeypatch.setenv("MCP_JWT_SECRET", "test-mcp-secret-0123456789012345")
    monkeypatch.setenv("MCP_AUTH_ISSUER", "http://localhost:8001")
    auth_module = importlib.reload(auth)
    server_module = importlib.reload(importlib.import_module("mcps.company_tools.server"))
    token = jwt.encode(
        {
            "iss": "http://localhost:8001",
            "sub": "test-subject",
            "client_id": "test-client",
            "scope": "incidents:read inventory:read",
        },
        "test-mcp-secret-0123456789012345",
        algorithm="HS256",
    )

    response = TestClient(server_module.app).get(
        "/mcp",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code != 401
    assert auth_module.MCP_AUTH.auth_info is None
