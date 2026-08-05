"""HealthCore vocabulary used by the RFP workflow."""

HEALTHCORE_DEPARTMENTS: tuple[str, ...] = (
    "Clinical Operations",
    "Patient Experience and Access",
    "Revenue Cycle and Billing",
    "Compliance and Data Governance",
    "People and Workforce",
    "Technology",
    "Executive Leadership",
)

DEPARTMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Clinical Operations": ("clinical", "clinic", "care delivery", "ehr", "patient record"),
    "Patient Experience and Access": ("booking", "appointment", "no-show", "reminder", "patient access"),
    "Revenue Cycle and Billing": ("claim", "payer", "denial", "billing", "reimbursement", "pricing"),
    "Compliance and Data Governance": ("hipaa", "gdpr", "privacy", "compliance", "security", "data retention"),
    "People and Workforce": ("staffing", "clinician", "employee", "hiring", "cme", "training", "workforce"),
    "Technology": ("api", "integration", "system", "uptime", "implementation", "architecture", "ehr"),
    "Executive Leadership": ("budget", "timeline", "governance", "milestone", "executive", "decision"),
}

CONTACT_ROLES: dict[str, str] = {
    "Clinical Operations": "Clinical Operations lead - Dr. Marcus Reid",
    "Patient Experience and Access": "Patient Experience and Access lead - Priya Nair",
    "Revenue Cycle and Billing": "Revenue Cycle and Billing lead - Tom Callahan",
    "Compliance and Data Governance": "Compliance and Data Governance lead - Claire Whitfield",
    "People and Workforce": "People and Workforce lead - Diane Foster",
    "Technology": "Technology lead - James Osei",
    "Executive Leadership": "Executive Leadership sponsor - Dr. Sandra Okonkwo",
}

# HealthCore's intake contract requires an RFP marker, a defined request/scope,
# and a commercial or submission detail before departmental work is started.
RFP_MARKERS = ("request for proposal", "rfp")
REQUIRED_SIGNAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("scope", "statement of work", "requirements", "deliverables"),
    ("submission deadline", "submission date", "due date", "proposal due", "deadline"),
    ("pricing", "budget", "cost", "commercial response", "fee"),
)
