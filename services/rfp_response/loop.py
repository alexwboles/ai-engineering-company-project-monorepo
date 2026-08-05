"""Bounded generator-evaluator loop with parallel evaluators."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from .evaluators.guidelines import evaluate_guidelines
from .evaluators.readability import evaluate_readability
from .evaluators.relevance import evaluate_relevance
from .models import EvaluationResult
from .orchestrator import generator_for_department

MAX_ITERATIONS = 3
Evaluator = Callable[[str, dict[str, Any]], EvaluationResult]
EVALUATORS: dict[str, Evaluator] = {
    "readability": evaluate_readability,
    "relevance": evaluate_relevance,
    "guidelines": evaluate_guidelines,
}


@dataclass(frozen=True)
class SectionLoopResult:
    department: str
    assigned_content: str
    evaluation: dict[str, Any]
    iterations: int
    needs_human_review: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "department": self.department,
            "assigned_content": self.assigned_content,
            "evaluation": self.evaluation,
            "iterations": self.iterations,
            "needs_human_review": self.needs_human_review,
        }


def evaluate_in_parallel(section: str, workstream: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Evaluators only read their section and workstream; they never share writes."""

    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        futures = {name: executor.submit(evaluator, section, workstream) for name, evaluator in EVALUATORS.items()}
        results = {name: futures[name].result().as_dict() for name in EVALUATORS}
    return results


def run_generator_evaluator_loop(
    workstream: dict[str, Any],
    metadata: dict[str, Any],
    *,
    max_iterations: int = MAX_ITERATIONS,
    generator: Any | None = None,
) -> SectionLoopResult:
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least one")

    selected_generator = generator or generator_for_department(str(workstream["department"]))
    feedback: list[str] = []
    latest_section = ""
    latest_results: dict[str, dict[str, Any]] = {}
    for iteration in range(1, max_iterations + 1):
        latest_section = selected_generator.generate(workstream, metadata, feedback)
        latest_results = evaluate_in_parallel(latest_section, workstream)
        passed = all(bool(result["passed"]) for result in latest_results.values())
        if passed:
            return SectionLoopResult(
                department=str(workstream["department"]),
                assigned_content=latest_section,
                evaluation={"passed": True, "iterations": iteration, "results": latest_results},
                iterations=iteration,
                needs_human_review=False,
            )
        feedback = [
            str(result["feedback"])
            for result in latest_results.values()
            if not result["passed"] and result.get("feedback")
        ]

    return SectionLoopResult(
        department=str(workstream["department"]),
        assigned_content=latest_section,
        evaluation={"passed": False, "iterations": max_iterations, "results": latest_results},
        iterations=max_iterations,
        needs_human_review=True,
    )
