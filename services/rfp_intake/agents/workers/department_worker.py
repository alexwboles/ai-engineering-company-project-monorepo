"""Department worker implementation; it only receives its assigned slice."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from ...constants import CONTACT_ROLES
from ..orchestrator import Workstream


@dataclass(frozen=True)
class WorkerResult:
    department: str
    key_aspects: list[str]
    open_questions: list[str]
    suggested_contact_role: str
    evidence_sections: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class DepartmentWorker:
    """Extract concise action points from one orchestrator-created workstream."""

    def run(self, workstream: Workstream) -> WorkerResult:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", workstream.prompt_context) if part.strip()]
        aspects = [sentence for sentence in sentences if len(sentence) > 12 and not sentence.startswith("##")][:4]
        questions = [sentence for sentence in sentences if "?" in sentence or any(word in sentence.lower() for word in ("must", "required", "confirm"))][:3]
        if not questions:
            questions = [f"What must {workstream.department} confirm before Sales submits the proposal?"]
        return WorkerResult(
            department=workstream.department,
            key_aspects=aspects or ["Review the assigned RFP workstream and identify operational requirements."],
            open_questions=questions,
            suggested_contact_role=CONTACT_ROLES[workstream.department],
            evidence_sections=workstream.section_refs,
        )


def run_department_worker(workstream: Workstream) -> dict[str, object]:
    return DepartmentWorker().run(workstream).as_dict()
