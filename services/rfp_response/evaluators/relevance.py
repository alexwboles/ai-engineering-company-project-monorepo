"""Checks that generated content answers the assigned Part 1 workstream."""

from __future__ import annotations

import re
from typing import Any

from ..models import EvaluationResult


STOP_WORDS = {"the", "and", "for", "with", "what", "must", "this", "that", "before", "from", "into"}


def evaluate_relevance(section: str, workstream: dict[str, Any]) -> EvaluationResult:
    asks = [str(item) for item in (workstream.get("needs") or workstream.get("key_aspects") or [])]
    normalized = section.casefold()
    missing: list[str] = []
    for ask in asks:
        terms = [term for term in re.findall(r"[a-z0-9]+", ask.casefold()) if len(term) > 3 and term not in STOP_WORDS]
        if not terms or sum(term in normalized for term in terms) < min(2, len(terms)):
            missing.append(ask)
    passed = not missing
    return EvaluationResult(
        evaluator="relevance",
        passed=passed,
        metrics={"asks_checked": len(asks), "unanswered_asks": missing},
        feedback=None if passed else f"Address these assigned RFP asks in the {workstream.get('department', 'department')} section: {'; '.join(missing)}.",
    )
