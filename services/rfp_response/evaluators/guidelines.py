"""Verifiable HealthCore guideline checklist evaluator."""

from __future__ import annotations

import re
from typing import Any

from ..models import EvaluationResult


PATIENT_IDENTIFIER = re.compile(r"\bHC-[A-Z0-9]{6}\b|\bpatient\s+(?:name|email|phone|id)\s*[:=]", re.I)
UNVERIFIED_COMMITMENT = re.compile(r"\b\d+(?:\.\d+)?%\s*(?:uptime|availability|reduction|increase)\b", re.I)


def evaluate_guidelines(section: str, _workstream: dict[str, Any]) -> EvaluationResult:
    failed_rules: list[str] = []
    feedback: list[str] = []
    lower = section.casefold()
    if PATIENT_IDENTIFIER.search(section):
        failed_rules.append("HC_GUIDELINE_NO_PATIENT_DATA")
        feedback.append("Remove patient identifiers or patient contact details from the draft.")
    if "hipaa" not in lower or "uk gdpr" not in lower:
        failed_rules.append("HC_GUIDELINE_DATA_PROTECTION")
        feedback.append("State how the proposal will be reviewed against HIPAA and UK GDPR.")
    if UNVERIFIED_COMMITMENT.search(section):
        failed_rules.append("HC_GUIDELINE_NO_INVENTED_COMMERCIALS")
        feedback.append("Remove the unverified numeric outcome or SLA commitment and mark it for confirmation.")
    if "### pricing" not in lower or "tbd" not in lower:
        failed_rules.append("HC_GUIDELINE_PRICING_ASSUMPTIONS")
        feedback.append("Include a Pricing section with a [TBD] confirmation placeholder.")
    if "owner for confirmation" not in lower or "next step" not in lower:
        failed_rules.append("HC_GUIDELINE_OPERATIONAL_TONE")
        feedback.append("End with a concrete next step and HealthCore owner.")
    return EvaluationResult(
        evaluator="guidelines",
        passed=not failed_rules,
        metrics={"rules_checked": 5},
        feedback=None if not feedback else " ".join(feedback),
        failed_rules=failed_rules or None,
    )
