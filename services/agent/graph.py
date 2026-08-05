"""Compiled LangGraph orchestration for the HealthCore support agent."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .harness.input_guards import classify_input
from .harness.observability import get_guardrail_trace, store_guardrail_trace
from .harness.output_guards import validate_agent_output
from .nodes import (
    lookup_inventory_node,
    lookup_ticket_node,
    no_context_node,
    query_node,
    receive_question,
    retrieve_node,
    route_intent,
    synthesize_answer_node,
    tool_failure_node,
)
from .state import AgentState


def after_receive(state: AgentState) -> str:
    return "end" if state.get("error") else "route_intent"


def after_route(state: AgentState) -> str:
    return {
        "rag": "retrieve",
        "ticket": "lookup_ticket",
        "inventory": "lookup_inventory",
        "both": "retrieve",
    }.get(state.get("route", "rag"), "retrieve")


def after_retrieve(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if state.get("route") == "both":
        return "lookup_ticket"
    return "no_context" if not state.get("retrieved_context") else "query"


def after_ticket(state: AgentState) -> str:
    if state.get("route") == "both":
        return "lookup_inventory"
    return "tool_failure" if _has_tool_failure(state) else "synthesize_answer"


def after_inventory(state: AgentState) -> str:
    return "tool_failure" if _has_tool_failure(state) else "synthesize_answer"


def build_agent_graph(checkpointer: Any | None = None):
    """Build and compile the graph; structural errors surface during startup."""

    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("route_intent", route_intent)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("lookup_ticket", lookup_ticket_node)
    builder.add_node("lookup_inventory", lookup_inventory_node)
    builder.add_node("no_context", no_context_node)
    builder.add_node("query", query_node)
    builder.add_node("handle_tool_failure", tool_failure_node)
    builder.add_node("synthesize_answer", synthesize_answer_node)
    builder.add_edge(START, "receive_question")
    builder.add_conditional_edges(
        "receive_question",
        after_receive,
        {"route_intent": "route_intent", "end": END},
    )
    builder.add_conditional_edges(
        "route_intent",
        after_route,
        {
            "retrieve": "retrieve",
            "lookup_ticket": "lookup_ticket",
            "lookup_inventory": "lookup_inventory",
        },
    )
    builder.add_conditional_edges(
        "retrieve",
        after_retrieve,
        {
            "query": "query",
            "no_context": "no_context",
            "lookup_ticket": "lookup_ticket",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "lookup_ticket",
        after_ticket,
        {
            "lookup_inventory": "lookup_inventory",
            "tool_failure": "handle_tool_failure",
            "synthesize_answer": "synthesize_answer",
        },
    )
    builder.add_conditional_edges(
        "lookup_inventory",
        after_inventory,
        {"tool_failure": "handle_tool_failure", "synthesize_answer": "synthesize_answer"},
    )
    builder.add_edge("query", END)
    builder.add_edge("no_context", END)
    builder.add_edge("handle_tool_failure", END)
    builder.add_edge("synthesize_answer", END)
    return builder.compile(checkpointer=checkpointer or MemorySaver())


def _has_tool_failure(state: AgentState) -> bool:
    return any(bool(item.get("error")) for item in state.get("tool_results", []))


_CHECKPOINTER = MemorySaver()
AGENT_GRAPH = build_agent_graph(_CHECKPOINTER)


def invoke_agent(question: str, *, trace_id: str | None = None) -> dict[str, Any]:
    run_id = trace_id or f"agent-{uuid4().hex}"
    decision = classify_input(question, trace_id=run_id)
    if decision.action != "allow":
        result = {
            "question": str(question or "").strip(),
            "route": "guardrail",
            "route_reason": decision.reason,
            "answer": decision.response,
            "final_answer": decision.response,
            "error": None,
            "trace_id": run_id,
            "trace_steps": [
                {
                    "node": "input_guardrail",
                    "order": 1,
                    "output_summary": f"action={decision.action}; guardrail={decision.guardrail}",
                }
            ],
            "trace": [
                {
                    "node": "input_guardrail",
                    "order": 1,
                    "output_summary": f"action={decision.action}; guardrail={decision.guardrail}",
                }
            ],
            "guardrail": decision.guardrail,
        }
        store_guardrail_trace(run_id, result)
        return result
    result = AGENT_GRAPH.invoke(
        {"question": question, "trace_id": run_id, "trace_steps": []},
        config={"configurable": {"thread_id": run_id}},
    )
    safe_answer = (
        None
        if result.get("error") and result.get("answer") is None
        else validate_agent_output(result.get("answer"), trace_id=run_id)
    )
    return {**result, "answer": safe_answer, "final_answer": safe_answer, "trace_id": run_id}


def get_agent_trace(trace_id: str) -> dict[str, Any] | None:
    snapshot = AGENT_GRAPH.get_state({"configurable": {"thread_id": trace_id}})
    if not snapshot or not snapshot.values:
        return get_guardrail_trace(trace_id)
    values = snapshot.values
    return {
        "trace_id": trace_id,
        "route": values.get("route"),
        "route_reason": values.get("route_reason"),
        "trace": values.get("trace_steps", []),
        "tool_results": values.get("tool_results", []),
        "answer": values.get("answer"),
        "error": values.get("error"),
    }
