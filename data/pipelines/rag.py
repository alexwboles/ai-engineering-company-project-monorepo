"""Small deterministic HealthCore knowledge-base primitives used by the agent graph.

The graph deliberately imports these functions instead of embedding retrieval
or answer-generation logic in a node. The implementation is local and
deterministic so tests do not require an external model or vector database.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_STOP_WORDS = {
    "a", "an", "and", "are", "about", "at", "by", "for", "from", "how", "in",
    "is", "of", "on", "or", "the", "to", "what", "where", "which", "with",
}

_KNOWLEDGE_BASE: tuple[dict[str, str], ...] = (
    {
        "id": "healthcore-compliance",
        "source": "CONTEXT_HEALTHCORE.md",
        "text": "HealthCore protects patient data under HIPAA in the United States and UK GDPR in the United Kingdom. Systems must control how patient data is stored, accessed, and shared.",
    },
    {
        "id": "healthcore-access",
        "source": "CONTEXT.md",
        "text": "Patient Experience and Access manages booking, appointment reminders, follow-up, and the patient journey. HealthCore currently reports a 22% no-show rate across the network.",
    },
    {
        "id": "healthcore-billing",
        "source": "CONTEXT.md",
        "text": "Revenue Cycle and Billing manages commercial insurance, Medicare, Medicaid, private pay, and NHS billing. HealthCore reports a 14% claim denial rate.",
    },
    {
        "id": "healthcore-workforce",
        "source": "CONTEXT_HEALTHCORE.md",
        "text": "People and Workforce manages approximately 200 employees, hiring, onboarding, training, and continuing medical education requirements for clinicians.",
    },
    {
        "id": "healthcore-operations",
        "source": "CONTEXT.md",
        "text": "Clinical Operations covers care delivery across 12 US and UK clinics. Technology owns integration across the legacy EHR, billing, scheduling, and operational systems.",
    },
)


def setup() -> list[dict[str, str]]:
    """Return the configured HealthCore knowledge base."""

    return [dict(chunk) for chunk in _KNOWLEDGE_BASE]


def embed(text: str) -> dict[str, int]:
    """Create a lightweight lexical embedding for deterministic local retrieval."""

    tokens = [token for token in _tokens(text) if token not in _STOP_WORDS]
    return dict(Counter(tokens))


def retrieve(question: str, *, top_k: int = 3, threshold: float = 0.0) -> list[dict[str, Any]]:
    """Return the most relevant HealthCore chunks without generating an answer."""

    question_vector = embed(question)
    if not question_vector:
        return []

    scored: list[dict[str, Any]] = []
    for chunk in setup():
        chunk_vector = embed(chunk["text"])
        overlap = sum(min(question_vector[token], chunk_vector[token]) for token in question_vector if token in chunk_vector)
        if overlap <= threshold:
            continue
        scored.append({**chunk, "score": float(overlap)})

    scored.sort(key=lambda item: (-float(item["score"]), str(item["id"])))
    return scored[: max(0, top_k)]


def generate_answer(question: str, context: list[dict[str, Any]]) -> str:
    """Generate a grounded answer from already-retrieved context only."""

    if not context:
        return "I don't have information about that in the HealthCore knowledge base."
    facts = " ".join(str(item["text"]) for item in context)
    return f"According to the HealthCore knowledge base: {facts}"


def query(question: str, context: list[dict[str, Any]] | None = None) -> str:
    """Compatibility helper; supplied context skips retrieval."""

    retrieved = context if context is not None else retrieve(question)
    return generate_answer(question, retrieved)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())
