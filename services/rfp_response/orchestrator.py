"""Assignment orchestrator mapping Part 1 workstreams to generators."""

from __future__ import annotations

from typing import Any

from .generators.base import DepartmentGenerator
from .generators.clinical_operations import ClinicalOperationsGenerator
from .generators.compliance_data_governance import ComplianceDataGovernanceGenerator
from .generators.executive_leadership import ExecutiveLeadershipGenerator
from .generators.patient_experience_access import PatientExperienceAccessGenerator
from .generators.people_workforce import PeopleWorkforceGenerator
from .generators.revenue_cycle_billing import RevenueCycleBillingGenerator
from .generators.technology import TechnologyGenerator


GENERATOR_TYPES: dict[str, type[DepartmentGenerator]] = {
    "Clinical Operations": ClinicalOperationsGenerator,
    "Patient Experience and Access": PatientExperienceAccessGenerator,
    "Revenue Cycle and Billing": RevenueCycleBillingGenerator,
    "Compliance and Data Governance": ComplianceDataGovernanceGenerator,
    "People and Workforce": PeopleWorkforceGenerator,
    "Technology": TechnologyGenerator,
    "Executive Leadership": ExecutiveLeadershipGenerator,
}


def generator_for_department(department: str) -> DepartmentGenerator:
    try:
        return GENERATOR_TYPES[department]()
    except KeyError as exc:
        raise ValueError(f"No HealthCore response generator is configured for {department}.") from exc


def generate_department_section(
    workstream: dict[str, Any],
    metadata: dict[str, Any],
    feedback: list[str] | None = None,
) -> str:
    generator = generator_for_department(str(workstream["department"]))
    return generator.generate(workstream, metadata, feedback)
