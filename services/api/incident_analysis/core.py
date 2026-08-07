from __future__ import annotations

import csv
import io
import math
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import (
    ALLOWED_CATEGORIES,
    ALLOWED_COUNTRIES,
    ALLOWED_STATUSES,
    CLINIC_ID_PATTERN,
    FORBIDDEN_PHI_FIELDS,
    PATIENT_ID_PATTERN,
    REQUIRED_FIELDS,
    SATISFACTION_MAX,
    SATISFACTION_MIN,
)
from .models import AnalysisSummary, InvalidRecord


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def _canonical(value: str | None) -> str:
    return _normalize(value).upper()


def _parse_satisfaction(raw_value: str) -> tuple[float | None, str | None]:
    raw = _normalize(raw_value)
    if raw == "":
        return None, None
    try:
        parsed = float(raw)
    except ValueError:
        return None, "invalid_number"

    if parsed < SATISFACTION_MIN or parsed > SATISFACTION_MAX:
        return None, "out_of_range"

    return parsed, None


def _validate_row(row: dict[str, str], row_number: int) -> list[InvalidRecord]:
    invalids: list[InvalidRecord] = []

    missing_fields = [field for field in REQUIRED_FIELDS if _normalize(row.get(field, "")) == ""]
    if missing_fields:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id", "")) or "<missing>",
                reason="missing_required_field",
                details=", ".join(missing_fields),
            )
        )
        return invalids

    category = _canonical(row.get("category"))
    status = _canonical(row.get("status"))

    clinic_id = _normalize(row.get("clinic_id"))
    country = _canonical(row.get("country"))
    patient_id = _normalize(row.get("patient_id")).upper()

    if not CLINIC_ID_PATTERN.fullmatch(clinic_id):
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="invalid_clinic_id",
                details="clinic_id must use the HealthCore country-clinic-number format",
            )
        )

    if country not in ALLOWED_COUNTRIES:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="invalid_country",
                details="country must be US or UK",
            )
        )
    elif clinic_id and clinic_id[:2].upper() != country:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="clinic_country_mismatch",
                details="clinic_id country prefix must match country",
            )
        )

    if not PATIENT_ID_PATTERN.fullmatch(patient_id):
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="invalid_patient_id",
                details="patient_id must be a pseudonymous HC-XXXXXX identifier",
            )
        )

    for field in FORBIDDEN_PHI_FIELDS:
        if _normalize(row.get(field)):
            invalids.append(
                InvalidRecord(
                    row_number=row_number,
                    incident_id=_normalize(row.get("incident_id")),
                    reason="forbidden_phi_field",
                    details=f"field '{field}' is not permitted in analysis input",
                )
            )
            break

    if category not in ALLOWED_CATEGORIES:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="invalid_category",
                details=f"category='{category}'",
            )
        )

    if status not in ALLOWED_STATUSES:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="invalid_status",
                details=f"status='{status}'",
            )
        )

    satisfaction_raw = _normalize(row.get("satisfaction_score", ""))
    if status == "CLOSED" and satisfaction_raw == "":
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason="missing_satisfaction_score",
                details="closed incidents require satisfaction_score",
            )
        )
    else:
        _, satisfaction_error = _parse_satisfaction(satisfaction_raw)
        if satisfaction_error is not None:
            invalids.append(
                InvalidRecord(
                    row_number=row_number,
                    incident_id=_normalize(row.get("incident_id")),
                    reason=satisfaction_error,
                    details=f"satisfaction_score='{satisfaction_raw}'",
                )
            )

    return invalids


def analyze_incident_rows(rows: Iterable[dict[str, str]]) -> tuple[AnalysisSummary, list[InvalidRecord], list[dict[str, str]]]:
    invalid_records: list[InvalidRecord] = []
    valid_rows: list[dict[str, str]] = []

    for index, row in enumerate(rows, start=2):
        row_issues = _validate_row(row, row_number=index)
        if row_issues:
            invalid_records.extend(row_issues)
            continue
        valid_rows.append(row)

    category_counter = Counter(_canonical(row.get("category")) for row in valid_rows)
    status_counter = Counter(_canonical(row.get("status")) for row in valid_rows)
    clinic_counter = Counter(_normalize(row.get("clinic_id")) for row in valid_rows)
    country_counter = Counter(_canonical(row.get("country")) for row in valid_rows)

    satisfaction_scores: list[float] = []
    for row in valid_rows:
        if _canonical(row.get("status")) != "CLOSED":
            continue
        score, _ = _parse_satisfaction(row.get("satisfaction_score", ""))
        if score is not None:
            satisfaction_scores.append(score)

    average_satisfaction = (
        round(sum(satisfaction_scores) / len(satisfaction_scores), 2) if satisfaction_scores else None
    )

    summary = AnalysisSummary(
        total_records=len(valid_rows) + len({(i.row_number, i.incident_id) for i in invalid_records}),
        valid_records=len(valid_rows),
        invalid_records=len({(i.row_number, i.incident_id) for i in invalid_records}),
        invalid_by_reason=dict(Counter(invalid.reason for invalid in invalid_records)),
        category_breakdown=dict(category_counter),
        status_breakdown=dict(status_counter),
        clinic_breakdown=dict(clinic_counter),
        country_breakdown=dict(country_counter),
        average_satisfaction_closed=average_satisfaction,
    )

    return summary, invalid_records, valid_rows


def load_and_analyze_csv(csv_path: str | Path) -> tuple[AnalysisSummary, list[InvalidRecord], list[dict[str, str]]]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return analyze_incident_csv_text(handle.read())


def analyze_incident_csv_text(
    text: str,
) -> tuple[AnalysisSummary, list[InvalidRecord], list[dict[str, str]]]:
    """Analyze CSV text so the CLI and API share one parsing and validation path."""
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if reader.fieldnames is None or any(not str(field).strip() for field in reader.fieldnames):
        raise ValueError("CSV file is missing a valid header row.")
    return analyze_incident_rows(reader)


def values_match_expected(actual: object, expected: object) -> bool:
    """Compare nested result values without false negatives from float rounding."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            values_match_expected(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, (int, float)) and not isinstance(actual, bool) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
    return actual == expected


def summary_to_dict(summary: AnalysisSummary) -> dict[str, object]:
    return asdict(summary)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
