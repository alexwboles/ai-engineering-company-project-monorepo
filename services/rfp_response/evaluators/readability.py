"""Readability evaluator for one department section."""

from __future__ import annotations

from typing import Any

from services.rfp_intake.metrics import compute_readability

from ..models import EvaluationResult


def evaluate_readability(section: str, _workstream: dict[str, Any]) -> EvaluationResult:
    metrics = compute_readability(section)
    grade = float(metrics.get("gunning_fog_grade", 99))
    passed = grade <= 14
    return EvaluationResult(
        evaluator="readability",
        passed=passed,
        metrics=metrics,
        feedback=None if passed else "Simplify this section into shorter sentences for an operations reader.",
    )
