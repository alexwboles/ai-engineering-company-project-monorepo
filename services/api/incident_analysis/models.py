from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class InvalidRecord:
    row_number: int
    incident_id: str
    reason: str
    details: str


@dataclass(slots=True)
class AnalysisSummary:
    total_records: int
    valid_records: int
    invalid_records: int
    invalid_by_reason: dict[str, int]
    category_breakdown: dict[str, int]
    status_breakdown: dict[str, int]
    clinic_breakdown: dict[str, int]
    country_breakdown: dict[str, int]
    average_satisfaction_closed: float | None
