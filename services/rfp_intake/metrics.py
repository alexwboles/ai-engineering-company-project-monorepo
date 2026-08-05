"""Metadata and readability estimates for RFP triage."""

from __future__ import annotations

import re
from typing import Any

from .constants import HEALTHCORE_DEPARTMENTS


def extract_metadata(markdown: str) -> dict[str, Any]:
    lower = markdown.lower()
    client_match = re.search(r"(?:client|issuer|issued\s+by|prepared\s+for)\s*[:\-]\s*([^\n]+)", markdown, re.I)
    deadline_match = re.search(
        r"(?:submission\s+deadline|submission\s+date|proposal\s+due|due\s+date|deadline)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
        markdown,
        re.I,
    )
    mentioned = [department for department in HEALTHCORE_DEPARTMENTS if department.lower() in lower]
    words = re.findall(r"\b[\w'-]+\b", markdown)
    pages = max(1, markdown.count("\f") + 1)
    return {
        "client": client_match.group(1).strip() if client_match else None,
        "submission_deadline": deadline_match.group(1) if deadline_match else None,
        "departments_mentioned": mentioned,
        "word_count": len(words),
        "page_count": pages,
    }


def compute_readability(markdown: str) -> dict[str, Any]:
    """Use py-readability-metrics; retain a safe fallback for local test runners."""

    try:
        from readability import Readability

        reader = Readability(markdown)
        flesch = reader.flesch_kincaid()
        fog = reader.gunning_fog()
        return {
            "flesch_kincaid_grade": round(float(flesch.score), 2),
            "gunning_fog_grade": round(float(fog.score), 2),
            "word_count": len(re.findall(r"\b[\w'-]+\b", markdown)),
            "complexity": _complexity_label(float(fog.score)),
        }
    except (ImportError, AttributeError, TypeError, ValueError):
        words = re.findall(r"\b[\w'-]+\b", markdown)
        sentences = max(1, len(re.findall(r"[.!?]+", markdown)))
        rough_grade = round(max(0.0, (len(words) / sentences) / 2.0), 2)
        return {
            "flesch_kincaid_grade": rough_grade,
            "gunning_fog_grade": rough_grade,
            "word_count": len(words),
            "complexity": _complexity_label(rough_grade),
            "source": "fallback-estimate",
        }


def _complexity_label(grade: float) -> str:
    if grade >= 14:
        return "high complexity"
    if grade >= 9:
        return "moderate complexity"
    return "lower complexity"
