"""Structured contracts shared by response generators and evaluators."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationResult:
    evaluator: str
    passed: bool
    metrics: dict[str, Any]
    feedback: str | None = None
    failed_rules: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DepartmentResponse:
    department: str
    assigned_content: str
    evaluation: dict[str, Any]
    iterations: int
    needs_human_review: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
