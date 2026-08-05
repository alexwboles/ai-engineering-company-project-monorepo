"""Deterministic validation and redaction for generated support answers."""

from __future__ import annotations

import re
from typing import Any

from .external_content import unwrap_external_markers
from .observability import record_guardrail_event


SAFE_OUTPUT = (
    "I can't provide that response because it did not meet HealthCore's safety "
    "requirements. Please ask about HealthCore operations or rephrase without "
    "patient identifiers."
)

_INTERNAL_MARKERS = (
    re.compile(r"\bsystem\s+(?:prompt|message|instructions?)\b", re.I),
    re.compile(r"\bdeveloper\s+(?:message|instructions?)\b", re.I),
    re.compile(r"\b(?:MCP_ACCESS_TOKEN|MCP_JWT_SECRET|RAG_API_KEY)\b", re.I),
    re.compile(r"\bignore\s+(?:the\s+)?(?:previous|system)\s+(?:instructions?|rules?)\b", re.I),
)
_PHI_MARKERS = (
    re.compile(r"\bHC-[A-Za-z0-9]{6}\b", re.I),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}[-.) ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)


def validate_agent_output(
    answer: Any,
    *,
    trace_id: str | None = None,
) -> str:
    """Return a safe plain string or a controlled refusal; never leak raw output."""

    if not isinstance(answer, str) or not answer.strip():
        record_guardrail_event(
            guardrail="output_shape",
            failure_type="structural",
            action="block",
            message="non-string or empty model output",
            trace_id=trace_id,
        )
        return SAFE_OUTPUT

    clean = unwrap_external_markers(answer)
    if len(clean) > 12000:
        record_guardrail_event(
            guardrail="output_shape",
            failure_type="structural",
            action="block",
            message="model output exceeded the maximum response length",
            trace_id=trace_id,
        )
        return SAFE_OUTPUT

    if any(pattern.search(clean) for pattern in _INTERNAL_MARKERS):
        record_guardrail_event(
            guardrail="output_instruction_leak",
            failure_type="security",
            action="block",
            message=clean,
            trace_id=trace_id,
        )
        return SAFE_OUTPUT

    if any(pattern.search(clean) for pattern in _PHI_MARKERS):
        record_guardrail_event(
            guardrail="output_phi",
            failure_type="content",
            action="block",
            message=clean,
            trace_id=trace_id,
        )
        return SAFE_OUTPUT

    return clean
