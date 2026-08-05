from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

INCIDENT_ALLOWED_STATUSES: tuple[str, ...] = (
    "open",
    "in_progress",
    "resolved",
    "discarded",
)

INCIDENT_ALLOWED_ORIGINS: tuple[str, ...] = (
    "customer",
    "branch",
    "internal",
)

INCIDENT_ALLOWED_CATEGORIES: tuple[str, ...] = (
    "complaint",
    "request",
    "operational_failure",
)

INCIDENT_BRANCH_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "central", "label": "Central"},
    {"value": "us-tx-001", "label": "US - Austin Central"},
    {"value": "us-fl-001", "label": "US - Miami"},
    {"value": "us-ga-001", "label": "US - Atlanta"},
    {"value": "uk-lon-001", "label": "UK - London"},
    {"value": "uk-man-001", "label": "UK - Manchester"},
)

INCIDENT_ALLOWED_BRANCHES: tuple[str, ...] = tuple(item["value"] for item in INCIDENT_BRANCH_OPTIONS)

STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "open": ("in_progress", "discarded"),
    "in_progress": ("resolved", "discarded"),
    "resolved": (),
    "discarded": (),
}

CSV_STATUS_MAP: dict[str, str] = {
    "open": "open",
    "in_progress": "in_progress",
    "closed": "resolved",
    "resolved": "resolved",
    "discarded": "discarded",
}

CSV_CATEGORY_MAP: dict[str, str] = {
    "complaint": "complaint",
    "request": "request",
    "operational_failure": "operational_failure",
}

LOCATION_TO_BRANCH_MAP: dict[str, str] = {
    "us-tx-001": "us-tx-001",
    "austin": "us-tx-001",
    "texas": "us-tx-001",
    "us-fl-001": "us-fl-001",
    "miami": "us-fl-001",
    "florida": "us-fl-001",
    "us-ga-001": "us-ga-001",
    "atlanta": "us-ga-001",
    "georgia": "us-ga-001",
    "uk-lon-001": "uk-lon-001",
    "london": "uk-lon-001",
    "uk-man-001": "uk-man-001",
    "manchester": "uk-man-001",
    "central": "central",
}

HISTORICAL_REQUIRED_FIELDS: tuple[str, ...] = (
    "incident_id",
    "created_at",
    "customer_id",
    "category",
    "status",
)

SATISFACTION_MIN = 1.0
SATISFACTION_MAX = 5.0


def _normalize(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _parse_created_at(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value:
        return None

    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = datetime.fromisoformat(f"{value}T00:00:00")
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def can_transition_status(current_status: str, new_status: str) -> bool:
    if current_status not in STATUS_TRANSITIONS:
        return False
    if new_status == current_status:
        return True
    return new_status in STATUS_TRANSITIONS[current_status]


def validate_incident_payload(
    payload: Mapping[str, object],
    *,
    allow_partial: bool = False,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    cleaned: dict[str, str] = {}
    errors: list[dict[str, str]] = []

    expected_fields = ("title", "description", "category", "status", "origin", "branch")

    for field in expected_fields:
        raw_value = payload.get(field)
        value = _normalize(raw_value)

        if not allow_partial or field in payload:
            if not value:
                errors.append({"field": field, "message": f"{field.replace('_', ' ').title()} is required."})
                continue

        if value:
            cleaned[field] = value

    category = cleaned.get("category")
    if category and category not in INCIDENT_ALLOWED_CATEGORIES:
        errors.append(
            {
                "field": "category",
                "message": f"Category must be one of: {', '.join(INCIDENT_ALLOWED_CATEGORIES)}.",
            }
        )

    status = cleaned.get("status")
    if status and status not in INCIDENT_ALLOWED_STATUSES:
        errors.append(
            {
                "field": "status",
                "message": f"Status must be one of: {', '.join(INCIDENT_ALLOWED_STATUSES)}.",
            }
        )

    origin = cleaned.get("origin")
    if origin and origin not in INCIDENT_ALLOWED_ORIGINS:
        errors.append(
            {
                "field": "origin",
                "message": f"Origin must be one of: {', '.join(INCIDENT_ALLOWED_ORIGINS)}.",
            }
        )

    branch = cleaned.get("branch")
    if branch and branch not in INCIDENT_ALLOWED_BRANCHES:
        errors.append(
            {
                "field": "branch",
                "message": f"Branch must be one of: {', '.join(INCIDENT_ALLOWED_BRANCHES)}.",
            }
        )

    return cleaned, errors


def map_csv_status(value: object) -> str | None:
    return CSV_STATUS_MAP.get(_normalize(value).lower())


def map_csv_category(value: object) -> str | None:
    return CSV_CATEGORY_MAP.get(_normalize(value).lower())


def map_csv_branch(row: Mapping[str, object]) -> str:
    possible_inputs = (
        _normalize(row.get("location")),
        _normalize(row.get("location_id")),
        _normalize(row.get("branch")),
    )

    for raw in possible_inputs:
        if not raw:
            continue

        mapped = LOCATION_TO_BRANCH_MAP.get(raw.lower())
        if mapped:
            return mapped

    return "central"


def validate_historical_csv_row(row: Mapping[str, object]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    missing_fields = [field for field in HISTORICAL_REQUIRED_FIELDS if not _normalize(row.get(field))]
    if missing_fields:
        errors.append(
            {
                "field": "missing_required_field",
                "message": f"Missing required field(s): {', '.join(missing_fields)}.",
            }
        )
        return errors

    if map_csv_category(row.get("category")) is None:
        errors.append(
            {
                "field": "category",
                "message": "Category could not be mapped from CSV row.",
            }
        )

    if map_csv_status(row.get("status")) is None:
        errors.append(
            {
                "field": "status",
                "message": "Status could not be mapped from CSV row.",
            }
        )

    satisfaction_raw = _normalize(row.get("satisfaction_index"))
    if satisfaction_raw:
        try:
            satisfaction = float(satisfaction_raw)
        except ValueError:
            errors.append(
                {
                    "field": "satisfaction_index",
                    "message": "Satisfaction index must be a number when provided.",
                }
            )
        else:
            if satisfaction < SATISFACTION_MIN or satisfaction > SATISFACTION_MAX:
                errors.append(
                    {
                        "field": "satisfaction_index",
                        "message": "Satisfaction index must be between 1 and 5.",
                    }
                )

    return errors


def transform_csv_row_to_incident_seed(
    row: Mapping[str, object],
) -> tuple[dict[str, str], str, list[dict[str, str]]]:
    errors: list[dict[str, str]] = []

    source_incident_id = _normalize(row.get("incident_id") or row.get("id"))
    if not source_incident_id:
        errors.append({"field": "incident_id", "message": "Incident identifier is missing in CSV row."})

    raw_description = _normalize(row.get("description") or row.get("notes") or row.get("title"))
    title = raw_description or f"Historical incident {source_incident_id}"
    description = raw_description or title

    raw_created_at = _normalize(row.get("created_at") or row.get("date"))
    created_at = _parse_created_at(raw_created_at)
    if created_at is None:
        errors.append({"field": "created_at", "message": "Created date is missing or invalid in CSV row."})

    status = map_csv_status(row.get("status"))
    if status is None:
        errors.append({"field": "status", "message": "Status could not be mapped from CSV row."})

    category = map_csv_category(row.get("category"))
    if category is None:
        errors.append({"field": "category", "message": "Category could not be mapped from CSV row."})

    payload: dict[str, str] = {
        "title": title,
        "description": description,
        "category": category or "",
        "status": status or "",
        "origin": "customer",
        "branch": map_csv_branch(row),
        "created_at": created_at or "",
    }

    return payload, source_incident_id, errors
