from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import (
    ALLOWED_CATEGORIES,
    ALLOWED_STATUSES,
    REQUIRED_FIELDS,
    SATISFACTION_MAX,
    SATISFACTION_MIN,
)
from .models import AnalysisSummary, InvalidRecord


def _normalize(value: str | None) -> str:
    return (value or "").strip()


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

    category = _normalize(row.get("category"))
    status = _normalize(row.get("status"))

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

    _, satisfaction_error = _parse_satisfaction(row.get("satisfaction_index", ""))
    if satisfaction_error is not None:
        invalids.append(
            InvalidRecord(
                row_number=row_number,
                incident_id=_normalize(row.get("incident_id")),
                reason=satisfaction_error,
                details=f"satisfaction_index='{_normalize(row.get('satisfaction_index', ''))}'",
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

    category_counter = Counter(_normalize(row.get("category")) for row in valid_rows)
    status_counter = Counter(_normalize(row.get("status")) for row in valid_rows)

    satisfaction_scores: list[float] = []
    for row in valid_rows:
        if _normalize(row.get("status")) != "closed":
            continue
        score, _ = _parse_satisfaction(row.get("satisfaction_index", ""))
        if score is not None:
            satisfaction_scores.append(score)

    average_satisfaction = (
        sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None
    )

    summary = AnalysisSummary(
        total_records=len(valid_rows) + len({(i.row_number, i.incident_id) for i in invalid_records}),
        valid_records=len(valid_rows),
        invalid_records=len({(i.row_number, i.incident_id) for i in invalid_records}),
        invalid_by_reason=dict(Counter(invalid.reason for invalid in invalid_records)),
        category_breakdown=dict(category_counter),
        status_breakdown=dict(status_counter),
        average_satisfaction_closed=average_satisfaction,
    )

    return summary, invalid_records, valid_rows


def load_and_analyze_csv(csv_path: str | Path) -> tuple[AnalysisSummary, list[InvalidRecord], list[dict[str, str]]]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path.name}")

    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("CSV file is missing a header row.")
            return analyze_incident_rows(reader)
    except UnicodeDecodeError:
        raise
    except OSError as exc:
        raise OSError(f"Unable to read CSV file: {path.name}") from exc


def summary_to_dict(summary: AnalysisSummary) -> dict[str, object]:
    return asdict(summary)


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
