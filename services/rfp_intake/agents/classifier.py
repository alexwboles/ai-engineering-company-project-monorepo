"""HealthCore RFP hard-gate classifier."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from ..constants import DEPARTMENT_KEYWORDS, HEALTHCORE_DEPARTMENTS, REQUIRED_SIGNAL_GROUPS, RFP_MARKERS


@dataclass(frozen=True)
class ClassificationResult:
    is_rfp: bool
    confidence: float
    reason: str
    detected_departments: list[str]
    unknown_departments: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_rfp(markdown: str) -> ClassificationResult:
    normalized = markdown.lower()
    has_rfp_marker = any(marker in normalized for marker in RFP_MARKERS)
    matched_groups = sum(any(signal in normalized for signal in group) for group in REQUIRED_SIGNAL_GROUPS)
    detected = [
        department
        for department in HEALTHCORE_DEPARTMENTS
        if department.lower() in normalized
        or any(keyword in normalized for keyword in DEPARTMENT_KEYWORDS[department])
    ]
    unknown = _unknown_department_mentions(markdown)
    is_rfp = has_rfp_marker and matched_groups == len(REQUIRED_SIGNAL_GROUPS)
    if is_rfp:
        reason = "The document contains the HealthCore RFP marker, scope or requirements, deadline, and commercial detail."
        confidence = min(0.99, 0.75 + (0.05 * len(detected)))
    else:
        reason = "The document is missing one or more required RFP signals: marker, scope, deadline, or commercial detail."
        confidence = 0.12 if not has_rfp_marker else 0.45

    return ClassificationResult(is_rfp, confidence, reason, detected, unknown)


def _unknown_department_mentions(markdown: str) -> list[str]:
    known = {department.casefold() for department in HEALTHCORE_DEPARTMENTS}
    matches = re.findall(r"(?:department|workstream)\s*[:\-]\s*([A-Za-z][A-Za-z &]+)", markdown, re.I)
    return sorted({match.strip() for match in matches if match.strip().casefold() not in known})
