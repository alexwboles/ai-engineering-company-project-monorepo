from __future__ import annotations

from pathlib import Path

# NOTE: These names must match the assignment context for incidents analysis.
REQUIRED_FIELDS: tuple[str, ...] = (
    "incident_id",
    "created_at",
    "customer_id",
    "category",
    "status",
)

OPTIONAL_FIELDS: tuple[str, ...] = (
    "satisfaction_index",
    "customer_email",
    "contact_phone",
    "notes",
)

ALLOWED_CATEGORIES: tuple[str, ...] = (
    "complaint",
    "request",
    "operational_failure",
)

ALLOWED_STATUSES: tuple[str, ...] = (
    "open",
    "closed",
    "discarded",
)

SATISFACTION_MIN = 1.0
SATISFACTION_MAX = 5.0

DEFAULT_EXPECTED_RESULTS_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "expected-results.json"
)
