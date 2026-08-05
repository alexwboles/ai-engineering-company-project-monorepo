"""Compiled LangGraph orchestration for the HealthCore support agent."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import no_context_node, query_node, receive_question, retrieve_node
from .state import AgentState


def after_receive(state: AgentState) -> str:
    return "end" if state.get("error") else "retrieve"


def after_retrieve(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "no_context" if not state.get("retrieved_context") else "query"


def build_agent_graph(checkpointer: Any | None = None):
    """Build and compile the graph; structural errors surface during startup."""

    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("no_context", no_context_node)
    builder.add_node("query", query_node)
    builder.add_edge(START, "receive_question")
    builder.add_conditional_edges("receive_question", after_receive, {"retrieve": "retrieve", "end": END})
    builder.add_conditional_edges(
        "retrieve",
        after_retrieve,
        {"query": "query", "no_context": "no_context", "end": END},
    )
    builder.add_edge("query", END)
    builder.add_edge("no_context", END)
    return builder.compile(checkpointer=checkpointer or MemorySaver())


_CHECKPOINTER = MemorySaver()
AGENT_GRAPH = build_agent_graph(_CHECKPOINTER)


def invoke_agent(question: str, *, trace_id: str | None = None) -> dict[str, Any]:
    run_id = trace_id or f"agent-{uuid4().hex}"
    result = AGENT_GRAPH.invoke(
        {"question": question, "trace_id": run_id, "trace_steps": []},
        config={"configurable": {"thread_id": run_id}},
    )
    return {**result, "trace_id": run_id}


def get_agent_trace(trace_id: str) -> dict[str, Any] | None:
    snapshot = AGENT_GRAPH.get_state({"configurable": {"thread_id": trace_id}})
    if not snapshot or not snapshot.values:
        return None
    values = snapshot.values
    return {
        "trace_id": trace_id,
        "trace": values.get("trace_steps", []),
        "answer": values.get("answer"),
        "error": values.get("error"),
    }
