"""MCP tool for the real HealthCore Incidents Manager API."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from pydantic import Field

from ..http import UpstreamError, request_upstream
from .common import instrument, require_tool_scope, validation_error


IncidentAction = Literal["create", "update", "get_status"]

INCIDENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "description": "Whether the operation succeeded."},
        "action": {"type": "string", "enum": ["create", "update", "get_status"]},
        "incident": {
            "type": ["object", "null"],
            "description": "HealthCore incident fields when the operation succeeds.",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "status": {"type": "string"},
                "origin": {"type": "string"},
                "branch": {"type": "string"},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string"},
            },
        },
        "incidents": {
            "type": "array",
            "description": "HealthCore incidents returned by a status-filtered lookup.",
            "items": {"type": "object"},
        },
        "error_code": {"type": ["string", "null"]},
        "message": {"type": ["string", "null"]},
    },
    "required": ["ok", "action"],
}


def _base_url() -> str:
    return os.getenv("INCIDENTS_API_BASE_URL", "http://localhost:8000").rstrip("/")


def _upstream_error(exc: UpstreamError, action: str) -> dict[str, Any]:
    return {
        "ok": False,
        "action": action,
        "error_code": exc.error_code,
        "message": exc.message,
    }


@instrument("manage_incident_ticket")
def manage_incident_ticket(
    action: IncidentAction,
    ticket_id: Annotated[int | None, Field(default=None, gt=0, description="Existing incident ID for update or status lookup.")] = None,
    title: Annotated[str | None, Field(default=None, description="Incident title, required for create.")] = None,
    description: Annotated[str | None, Field(default=None, description="Incident description, required for create.")] = None,
    category: Annotated[str | None, Field(default=None, description="HealthCore incident category, required for create.")] = None,
    status: Annotated[str | None, Field(default=None, description="Lifecycle status; required for create and update.")] = None,
    origin: Annotated[str | None, Field(default=None, description="Incident origin, required for create.")] = None,
    branch: Annotated[str | None, Field(default=None, description="HealthCore branch, required for create.")] = None,
) -> dict[str, Any]:
    """Create, update, or check a HealthCore incident ticket.

    Requires incidents:read for get_status and incidents:write for create/update.
    Updates are restricted to PATCH /api/incidents/{id}/status so lifecycle rules
    remain enforced by the existing Incidents Manager.
    """

    require_tool_scope("incidents:read" if action == "get_status" else "incidents:write")
    if action == "get_status":
        if ticket_id is None and not status:
            raise validation_error("ticket_id or status is required for get_status")
        path = (
            f"{_base_url()}/api/incidents/{ticket_id}"
            if ticket_id is not None
            else f"{_base_url()}/api/incidents"
        )
        try:
            payload = request_upstream(
                "GET",
                path,
                params={"status": status} if ticket_id is None else None,
            )
        except UpstreamError as exc:
            return _upstream_error(exc, action)
        if ticket_id is None:
            return {"ok": True, "action": action, "incidents": payload}
        return {"ok": True, "action": action, "incident": payload}

    if action == "update":
        if ticket_id is None or not status:
            raise validation_error("ticket_id and status are required for update")
        try:
            incident = request_upstream(
                "PATCH",
                f"{_base_url()}/api/incidents/{ticket_id}/status",
                json={"status": status},
            )
        except UpstreamError as exc:
            return _upstream_error(exc, action)
        return {"ok": True, "action": action, "incident": incident}

    required = {
        "title": title,
        "description": description,
        "category": category,
        "status": status,
        "origin": origin,
        "branch": branch,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise validation_error(f"create requires: {', '.join(missing)}")
    try:
        incident = request_upstream(
            "POST",
            f"{_base_url()}/api/incidents",
            json=required,  # type: ignore[arg-type]
        )
    except UpstreamError as exc:
        return _upstream_error(exc, action)
    return {"ok": True, "action": action, "incident": incident}
