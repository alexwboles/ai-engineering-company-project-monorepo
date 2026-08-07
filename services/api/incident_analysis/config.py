from __future__ import annotations

import re
from pathlib import Path

# These fields and values are the HealthCore incident-analysis contract. The
# analyzer accepts no customer-support vocabulary from the earlier prototype.
REQUIRED_FIELDS: tuple[str, ...] = (
    "incident_id",
    "created_at",
    "clinic_id",
    "country",
    "patient_id",
    "category",
    "status",
)

OPTIONAL_FIELDS: tuple[str, ...] = (
    "satisfaction_score",
    "description",
)

ALLOWED_CATEGORIES: tuple[str, ...] = ("APPOINTMENT", "BILLING")
ALLOWED_STATUSES: tuple[str, ...] = ("OPEN", "CLOSED", "DISCARDED")
ALLOWED_COUNTRIES: tuple[str, ...] = ("US", "UK")

# HealthCore uses pseudonymous patient identifiers. Names, contact details,
# diagnoses, and medical-record identifiers must never enter the analysis.
PATIENT_ID_PATTERN = re.compile(r"^HC-[A-Z0-9]{6}$")
CLINIC_ID_PATTERN = re.compile(r"^(us|uk)-[a-z]{2,4}-\d{3}$", re.IGNORECASE)
FORBIDDEN_PHI_FIELDS: frozenset[str] = frozenset(
    {
        "patient_name",
        "patient_email",
        "email",
        "phone",
        "contact_phone",
        "address",
        "date_of_birth",
        "diagnosis",
        "medical_record_number",
        "ssn",
    }
)

SATISFACTION_MIN = 1.0
SATISFACTION_MAX = 5.0

DEFAULT_EXPECTED_RESULTS_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "expected-results.json"
)
