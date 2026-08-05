"""Structured guardrail events and process-local trigger counters."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from typing import Literal


logger = logging.getLogger("healthcore.agent.guardrails")
FailureType = Literal["structural", "content", "security"]

_COUNTERS: Counter[str] = Counter()
_LOCK = Lock()
_TRACE_RESULTS: dict[str, dict[str, object]] = {}
_PREVIEW_REPLACEMENTS = (
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[redacted-email]"),
    (re.compile(r"\bHC-[A-Za-z0-9]{6}\b", re.IGNORECASE), "[redacted-patient-id]"),
    (re.compile(r"\b\d{3}[-.) ]\d{3}[-. ]\d{4}\b"), "[redacted-phone]"),
)


def _safe_preview(message: str) -> str:
    preview = str(message).replace("\r", " ").replace("\n", " ").strip()[:160]
    for pattern, replacement in _PREVIEW_REPLACEMENTS:
        preview = pattern.sub(replacement, preview)
    return preview


def record_guardrail_event(
    *,
    guardrail: str,
    failure_type: FailureType,
    action: Literal["block", "redirect"],
    message: str,
    trace_id: str | None = None,
) -> None:
    """Log a safe structured event and increment its summary counters."""

    with _LOCK:
        _COUNTERS[failure_type] += 1
        if action == "redirect":
            _COUNTERS["redirects"] += 1
        else:
            _COUNTERS["blocks"] += 1
    logger.warning(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrail": guardrail,
                "failure_type": failure_type,
                "action": action,
                "trace_id": trace_id,
                "message_preview": _safe_preview(message),
            },
            sort_keys=True,
        )
    )


def guardrail_summary() -> dict[str, int]:
    """Return counts suitable for a test-session or operational summary."""

    with _LOCK:
        return {
            "security": _COUNTERS["security"],
            "content": _COUNTERS["content"],
            "structural": _COUNTERS["structural"],
            "redirects": _COUNTERS["redirects"],
            "blocks": _COUNTERS["blocks"],
        }


def store_guardrail_trace(trace_id: str, result: dict[str, object]) -> None:
    with _LOCK:
        _TRACE_RESULTS[trace_id] = dict(result)


def get_guardrail_trace(trace_id: str) -> dict[str, object] | None:
    with _LOCK:
        result = _TRACE_RESULTS.get(trace_id)
        return dict(result) if result else None


def reset_guardrail_observability() -> None:
    """Reset process-local counters for deterministic test sessions."""

    with _LOCK:
        _COUNTERS.clear()
        _TRACE_RESULTS.clear()
