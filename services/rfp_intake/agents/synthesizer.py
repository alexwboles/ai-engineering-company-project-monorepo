"""Sales-facing synthesizer for departmental worker results."""

from __future__ import annotations

from typing import Any


def synthesize_rfp(
    *,
    metadata: dict[str, Any],
    readability: dict[str, Any],
    worker_results: list[dict[str, Any]],
    unknown_departments: list[str] | None = None,
) -> dict[str, Any]:
    by_department = [
        {
            "department": result["department"],
            "needs": result["open_questions"] or result["key_aspects"],
            "key_aspects": result["key_aspects"],
            "contact": result["suggested_contact_role"],
            "evidence_sections": result["evidence_sections"],
        }
        for result in worker_results
    ]
    if unknown_departments:
        by_department.append(
            {
                "department": "Technology",
                "needs": [f"Clarify the requested department: {name}." for name in unknown_departments],
                "key_aspects": [],
                "contact": "Technology lead - James Osei",
                "evidence_sections": ["Routing clarification"],
            }
        )
    return {
        "summary": f"RFP from {metadata.get('client') or 'an unidentified issuer'} - due {metadata.get('submission_deadline') or 'date not found'}.",
        "by_department": by_department,
        "readability_estimate": readability.get("complexity", "complexity unavailable"),
        "routing_next": "proposal_generation_queue",
    }
