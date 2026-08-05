"""Concrete proposal rules derived from the HealthCore context."""

HEALTHCORE_GUIDELINES: tuple[dict[str, str], ...] = (
    {
        "id": "HC_GUIDELINE_NO_PATIENT_DATA",
        "description": "Proposal drafts must not include patient identifiers, diagnoses, or contact details.",
    },
    {
        "id": "HC_GUIDELINE_DATA_PROTECTION",
        "description": "Data-handling commitments must acknowledge HIPAA and UK GDPR.",
    },
    {
        "id": "HC_GUIDELINE_NO_INVENTED_COMMERCIALS",
        "description": "Do not invent pricing, outcomes, uptime, or service-level commitments; use confirmation placeholders.",
    },
    {
        "id": "HC_GUIDELINE_PRICING_ASSUMPTIONS",
        "description": "Every pricing proposal section must label pricing as TBD until Revenue Cycle and Billing confirms it.",
    },
    {
        "id": "HC_GUIDELINE_OPERATIONAL_TONE",
        "description": "Use clear, evidence-based language and end with an actionable HealthCore owner or question.",
    },
)
