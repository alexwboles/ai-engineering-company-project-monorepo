"""HealthCore-specific memory eligibility and self-evaluation policy."""

from __future__ import annotations

import re
from uuid import uuid4

from .models import MemoryProposal


_DOMAIN_TERMS = (
    "healthcore",
    "clinic",
    "appointment",
    "booking",
    "no-show",
    "no show",
    "claim",
    "billing",
    "denial",
    "payer",
    "cme",
    "clinician",
    "workforce",
    "licence",
    "license",
    "hipaa",
    "gdpr",
    "ehr",
    "incident",
    "ticket",
    "inventory",
    "stock",
    "product",
    "policy",
    "procedure",
    "compliance",
    "revenue cycle",
)
_MEMORY_SIGNALS = (
    "actually",
    "correction",
    "correct",
    "changed",
    "updated",
    "new policy",
    "from now on",
    "remember that",
    "resolved",
    "we fixed",
    "workflow is",
    "process is",
)
_FORBIDDEN_PATTERNS = (
    re.compile(r"\bHC-[A-Za-z0-9]{6}\b", re.I),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}[-.) ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(password|passphrase|secret|token|api[_ -]?key|credential)\b", re.I),
    re.compile(r"\b(patient|employee|clinician)\b.{0,60}\b(name|address|phone|salary|diagnosis|record)\b", re.I | re.S),
)
_LEADING_LANGUAGE = re.compile(
    r"^\s*(?:please\s+)?(?:remember that|remember|actually|correction\s*:?|correct(?:ion)?\s*:?)\s*",
    re.I,
)


def is_forbidden_memory(text: str) -> bool:
    return any(pattern.search(text) for pattern in _FORBIDDEN_PATTERNS)


def _memory_keys(text: str) -> tuple[str, ...]:
    lowered = text.casefold()
    keys: list[str] = []
    for term, key in (
        ("claim", "claims"),
        ("billing", "billing"),
        ("denial", "denials"),
        ("appointment", "appointments"),
        ("no-show", "no_shows"),
        ("cme", "cme"),
        ("clinician", "workforce"),
        ("incident", "incidents"),
        ("inventory", "inventory"),
        ("stock", "inventory"),
        ("hipaa", "compliance"),
        ("gdpr", "compliance"),
        ("policy", "policy"),
        ("procedure", "procedure"),
    ):
        if term in lowered and key not in keys:
            keys.append(key)
    return tuple(keys or ["healthcore_operations"])


def propose_memory(question: str, answer: str | None) -> MemoryProposal | None:
    """Self-evaluate a turn using explicit, conservative eligibility criteria.

    A proposal requires a reusable correction/update signal, a HealthCore topic,
    and a non-empty safe answer. Questions, thanks, one-off lookups, and any
    forbidden sensitive content are deliberately dismissed.
    """

    source = str(question or "").strip()
    response = str(answer or "").strip()
    lowered = source.casefold()
    if not source or not response or response.startswith("I don't have information"):
        return None
    if "?" in source and not any(signal in lowered for signal in ("remember that", "from now on")):
        return None
    if not any(signal in lowered for signal in _MEMORY_SIGNALS):
        return None
    if not any(term in lowered for term in _DOMAIN_TERMS):
        return None
    if is_forbidden_memory(source) or is_forbidden_memory(response):
        return None

    fact = _LEADING_LANGUAGE.sub("", source).strip(" .!?\n\t")
    if len(fact) < 12 or len(fact) > 500:
        return None
    return MemoryProposal(
        proposal_id=f"mem-{uuid4().hex}",
        action="upsert",
        fact=fact,
        reason="Reusable de-identified HealthCore operational correction or resolution pattern.",
        keys=_memory_keys(fact),
    )
