"""Orchestrator that assigns relevant Markdown slices to departments."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from ..constants import DEPARTMENT_KEYWORDS, HEALTHCORE_DEPARTMENTS


@dataclass(frozen=True)
class Workstream:
    department: str
    section_refs: list[str]
    prompt_context: str
    unknown_department_notes: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_workstreams(markdown: str, departments: list[str], unknown_departments: list[str] | None = None) -> list[Workstream]:
    sections = _split_sections(markdown)
    result: list[Workstream] = []
    unknown_notes = [f"Unrecognized department mentioned: {name}. Route clarification to Technology." for name in (unknown_departments or [])]
    for department in departments or list(HEALTHCORE_DEPARTMENTS):
        keywords = DEPARTMENT_KEYWORDS[department]
        matching = [(title, body) for title, body in sections if any(keyword in f"{title} {body}".lower() for keyword in keywords)]
        if not matching:
            continue
        result.append(
            Workstream(
                department=department,
                section_refs=[title for title, _ in matching],
                prompt_context="\n\n".join(f"## {title}\n{body}" for title, body in matching)[:6000],
                unknown_department_notes=unknown_notes if department == "Technology" else [],
            )
        )

    if unknown_notes and not any(item.department == "Technology" for item in result):
        result.append(
            Workstream(
                department="Technology",
                section_refs=["Routing clarification"],
                prompt_context="\n".join(unknown_notes),
                unknown_department_notes=unknown_notes,
            )
        )
    return result


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", markdown))
    if not matches:
        return [("Document overview", markdown[:6000])]
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end() : body_end].strip()
        if body:
            sections.append((match.group(1).strip(), body))
    return sections
