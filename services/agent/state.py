"""Minimal state contract passed between support-agent graph nodes."""

from __future__ import annotations

from typing import Any, Annotated, TypedDict
import operator


class TraceStep(TypedDict):
    node: str
    order: int
    output_summary: str


class AgentState(TypedDict, total=False):
    question: str
    retrieved_context: list[dict[str, Any]]
    answer: str | None
    error: str | None
    trace_id: str
    trace_steps: Annotated[list[TraceStep], operator.add]
