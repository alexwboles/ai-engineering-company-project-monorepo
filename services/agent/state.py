"""Minimal state contract passed between support-agent graph nodes."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class TraceStep(TypedDict):
    node: str
    order: int
    output_summary: str


class AgentState(TypedDict, total=False):
    question: str
    route: str
    route_reason: str
    requested_tools: list[str]
    retrieved_context: list[dict[str, Any]]
    memory_context: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    answer: str | None
    final_answer: str | None
    error: str | None
    trace_id: str
    trace_steps: Annotated[list[TraceStep], operator.add]
