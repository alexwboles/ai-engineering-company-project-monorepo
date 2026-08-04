"""Shared generator mechanics; department modules provide the domain emphasis."""

from __future__ import annotations

from typing import Any


class DepartmentGenerator:
    department = "HealthCore department"
    emphasis = "the assigned HealthCore operational requirements"

    def generate(
        self,
        workstream: dict[str, Any],
        metadata: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> str:
        needs = [str(value) for value in (workstream.get("needs") or [])]
        aspects = [str(value) for value in (workstream.get("key_aspects") or [])]
        contact = str(workstream.get("contact") or "the relevant HealthCore lead")
        requested = needs or aspects or [f"Confirm {self.emphasis}."]
        requested_lines = "\n".join(f"- {item}" for item in requested)
        feedback_block = ""
        if feedback:
            feedback_block = "\n### Revision feedback addressed\n" + "\n".join(f"- {item}" for item in feedback)

        return f"""## {self.department} pricing proposal section

### Requirements addressed
This section addresses the RFP needs assigned to {self.department}:
{requested_lines}

### HealthCore delivery approach
HealthCore Digital will validate the {self.emphasis} with {contact} before the proposal is finalized. The approach must work across HealthCore's US and UK clinic network and must account for the existing operational systems described in the RFP.

### Pricing and commercial assumptions
Pricing: [TBD - Revenue Cycle and Billing confirmation required]. No unapproved price, outcome, uptime, or service-level commitment is included in this draft.

### Compliance and data handling
Any handling of operational or patient-related data will be reviewed against HIPAA and UK GDPR. This draft contains no patient identifiers, diagnoses, or patient contact details.

### Questions and next step
{requested_lines}
Owner for confirmation: {contact}.
{feedback_block}
"""
