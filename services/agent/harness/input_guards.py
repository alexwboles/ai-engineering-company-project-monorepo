"""Input guardrails for scope control and instruction integrity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .observability import record_guardrail_event


GuardAction = Literal["allow", "block", "redirect"]


@dataclass(frozen=True)
class GuardDecision:
    action: GuardAction
    response: str | None = None
    failure_type: Literal["content", "security"] | None = None
    guardrail: str | None = None
    reason: str = ""


_INSTRUCTION_OVERRIDE_PATTERNS = (
    re.compile(r"\b(ignore|disregard|override)\b.{0,100}\b(previous|system|developer)?\s*(instructions|rules|prompt)\b", re.I | re.S),
    re.compile(r"\b(you are now|act as|pretend to be)\b.{0,100}\b(unrestricted|unfiltered|without rules|no rules|general(?:[- ]purpose)? assistant)\b", re.I | re.S),
    re.compile(r"\b(forget|erase|rewrite|change)\b.{0,100}\b(you work for healthcore|your instructions|the system prompt|the rules)\b", re.I | re.S),
    re.compile(r"\b(no rules|without rules|unrestricted mode|developer mode)\b", re.I),
)

_PERSONAL_USE_PATTERNS = (
    re.compile(r"\b(write|draft|compose)\b.{0,80}\b(essay|love poem|poem|homework|school assignment)\b", re.I | re.S),
    re.compile(r"\b(help me with|do)\b.{0,80}\b(my homework|my university (?:work|homework)|a personal project|unrelated code)\b", re.I | re.S),
    re.compile(r"\b(write|generate|build)\b.{0,80}\b(code|software)\b.{0,80}\b(another|unrelated|personal)\b", re.I | re.S),
    re.compile(r"\b(act as|be)\b.{0,40}\b(my therapist|my life coach|my personal assistant)\b", re.I | re.S),
    re.compile(r"\b(therapy|relationship advice|personal legal advice)\b", re.I),
)

_HEALTHCORE_DOMAIN_TERMS = (
    "healthcore",
    "clinic",
    "patient",
    "appointment",
    "booking",
    "no-show",
    "no show",
    "claim",
    "billing",
    "payer",
    "denial",
    "cme",
    "clinician",
    "doctor",
    "nurse",
    "licence",
    "license",
    "hipaa",
    "gdpr",
    "ehr",
    "incident",
    "ticket",
    "support case",
    "inventory",
    "stock",
    "product",
    "sku",
    "policy",
    "procedure",
    "compliance",
    "revenue cycle",
    "cme",
)

_SECURITY_RESPONSE = (
    "I can't change or ignore my system instructions. I'm here to support HealthCore "
    "operations and compliance. How can I help with that?"
)
_PERSONAL_RESPONSE = (
    "I can't help with personal tasks unrelated to HealthCore. I can help with "
    "clinic operations, appointments, claims, billing, compliance, workforce, "
    "incidents, and inventory."
)
_CASUAL_RESPONSE = (
    "I'm the HealthCore support assistant. I can give brief general context, but "
    "my purpose is HealthCore operations and compliance. What would you like to "
    "know about our clinics, appointments, claims, workforce, or policies?"
)


def _matches(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def classify_input(question: str, *, trace_id: str | None = None) -> GuardDecision:
    """Classify a user message before it can reach tools, RAG, or generation."""

    text = str(question or "").strip()
    if not text:
        return GuardDecision(action="allow", reason="empty input is handled by the graph")

    if _matches(_INSTRUCTION_OVERRIDE_PATTERNS, text):
        record_guardrail_event(
            guardrail="instruction_override",
            failure_type="security",
            action="block",
            message=text,
            trace_id=trace_id,
        )
        return GuardDecision(
            action="block",
            response=_SECURITY_RESPONSE,
            failure_type="security",
            guardrail="instruction_override",
            reason="instruction-change request",
        )

    if _matches(_PERSONAL_USE_PATTERNS, text):
        record_guardrail_event(
            guardrail="personal_use",
            failure_type="content",
            action="block",
            message=text,
            trace_id=trace_id,
        )
        return GuardDecision(
            action="block",
            response=_PERSONAL_RESPONSE,
            failure_type="content",
            guardrail="personal_use",
            reason="unrelated personal request",
        )

    if not any(term in text.casefold() for term in _HEALTHCORE_DOMAIN_TERMS):
        record_guardrail_event(
            guardrail="out_of_scope",
            failure_type="content",
            action="redirect",
            message=text,
            trace_id=trace_id,
        )
        return GuardDecision(
            action="redirect",
            response=_CASUAL_RESPONSE,
            failure_type="content",
            guardrail="out_of_scope",
            reason="casual or out-of-domain request",
        )

    return GuardDecision(action="allow", reason="HealthCore domain term detected")
