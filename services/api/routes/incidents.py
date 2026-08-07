from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

try:
    from services.api.auth_security import get_current_user
    from services.api.incidents_service import IncidentsService
except ModuleNotFoundError:
    from auth_security import get_current_user
    from incidents_service import IncidentsService

try:
    from packages.shared.incident_manager_validation import (
        INCIDENT_ALLOWED_BRANCHES,
        INCIDENT_ALLOWED_CATEGORIES,
        INCIDENT_ALLOWED_ORIGINS,
        INCIDENT_ALLOWED_STATUSES,
        can_transition_status,
        validate_incident_payload,
    )
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[3]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from packages.shared.incident_manager_validation import (  # type: ignore
        INCIDENT_ALLOWED_BRANCHES,
        INCIDENT_ALLOWED_CATEGORIES,
        INCIDENT_ALLOWED_ORIGINS,
        INCIDENT_ALLOWED_STATUSES,
        can_transition_status,
        validate_incident_payload,
    )

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _format_validation_errors(errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "loc": ["body", error["field"]],
            "msg": error["message"],
            "type": "value_error",
        }
        for error in errors
    ]


def _validate_filter(name: str, value: str | None, allowed_values: tuple[str, ...]) -> None:
    if value is not None and value not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[
                {
                    "loc": ["query", name],
                    "msg": f"{name.replace('_', ' ').title()} must be one of: {', '.join(allowed_values)}.",
                    "type": "value_error",
                }
            ],
        )


@router.post("")
def create_incident(payload: dict[str, object] = Body(...), current_user=Depends(get_current_user)) -> dict[str, Any]:
    _ = current_user
    cleaned, errors = validate_incident_payload(payload)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_format_validation_errors(errors))

    return IncidentsService.create_incident(cleaned)


@router.get("")
def list_incidents(
    status: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    category: str | None = None,
    current_user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    _ = current_user

    _validate_filter("status", status, INCIDENT_ALLOWED_STATUSES)
    _validate_filter("origin", origin, INCIDENT_ALLOWED_ORIGINS)
    _validate_filter("branch", branch, INCIDENT_ALLOWED_BRANCHES)
    _validate_filter("category", category, INCIDENT_ALLOWED_CATEGORIES)

    return IncidentsService.list_incidents(status=status, origin=origin, branch=branch, category=category)


@router.get("/summary")
def incidents_summary(current_user=Depends(get_current_user)) -> dict[str, Any]:
    _ = current_user
    return IncidentsService.get_summary()


@router.get("/{incident_id}")
def get_incident(incident_id: int, current_user=Depends(get_current_user)) -> dict[str, Any]:
    _ = current_user
    incident = IncidentsService.get_incident_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    return incident


@router.patch("/{incident_id}/status")
def update_incident_status(
    incident_id: int,
    payload: dict[str, object] = Body(...),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    _ = current_user

    cleaned, errors = validate_incident_payload({"status": payload.get("status")}, allow_partial=True)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_format_validation_errors(errors))

    next_status = cleaned.get("status", "")

    incident = IncidentsService.get_incident_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    current_status = str(incident.get("status", ""))
    if not can_transition_status(current_status, next_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status transition for incident lifecycle.",
        )

    updated = IncidentsService.update_incident_status(incident_id, next_status)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    return updated
