"""Explicit classification of a user's response to one pending proposal."""

from __future__ import annotations

import re

from .models import ConfirmationDecision, MemoryProposal
from .policy import is_forbidden_memory


_APPROVE = re.compile(
    r"^\s*(?:yes|y|approve|approved|save|remember(?:\s+it)?|go\s+ahead|do\s+it)"
    r"(?:\s*(?:please\s+)?(?:remember|save|store)(?:\s+(?:it|that))?)?"
    r"(?:\s*(?:,|and|also)\s+(?P<remainder>.+?))?\s*[.!?]?\s*$",
    re.I | re.S,
)
_REJECT = re.compile(
    r"^\s*(?:no|nope|reject|decline|not\s+now|forget\s+it|don't\s+remember|do\s+not\s+remember)"
    r"(?:\s*(?:,|and|also)\s+(?P<remainder>.+?))?\s*[.!?]?\s*$",
    re.I | re.S,
)
_EDIT = re.compile(
    r"^\s*(?:edit|change|update|instead)\s*(?:the\s+fact\s*)?[:,-]\s*(?P<fact>.+?)\s*[.!?]?\s*$",
    re.I | re.S,
)


def classify_confirmation(message: str, proposal: MemoryProposal) -> ConfirmationDecision:
    """Return a structured decision; silence and ambiguous text are rejection."""

    text = str(message or "").strip()
    if match := _APPROVE.fullmatch(text):
        remainder = (match.group("remainder") or "").strip()
        return ConfirmationDecision("approve", remainder=remainder, reason="explicit approval label")
    if match := _REJECT.fullmatch(text):
        remainder = (match.group("remainder") or "").strip()
        return ConfirmationDecision("reject", remainder=remainder, reason="explicit rejection label")
    if match := _EDIT.fullmatch(text):
        fact = (match.group("fact") or "").strip()
        if is_forbidden_memory(fact):
            return ConfirmationDecision("reject", reason="edited fact violates HealthCore memory policy")
        return ConfirmationDecision("edit", edited_fact=fact, reason="explicit edit label")
    return ConfirmationDecision(
        "unclear",
        reason=f"message did not clearly classify against proposal {proposal.proposal_id}",
    )
