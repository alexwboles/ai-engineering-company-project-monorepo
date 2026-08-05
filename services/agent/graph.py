"""Compiled LangGraph orchestration for the HealthCore support agent."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .harness.input_guards import classify_input
from .harness.observability import get_guardrail_trace, store_guardrail_trace
from .harness.output_guards import validate_agent_output
from .memory.confirm import classify_confirmation
from .memory.models import MemoryProposal
from .memory.policy import propose_memory
from .memory.store import MemoryStore, get_default_memory_store
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
    return "no_context" if not (state.get("retrieved_context") or state.get("memory_context")) else "query"


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


def invoke_agent(
    question: str,
    *,
    trace_id: str | None = None,
    session_id: str | None = None,
    memory_store: MemoryStore | None = None,
) -> dict[str, Any]:
    run_id = trace_id or f"agent-{uuid4().hex}"
    conversation_id = session_id or run_id
    store = memory_store or get_default_memory_store()
    current_question = str(question or "").strip()
    confirmation_note = ""

    pending = store.get_pending(conversation_id)
    if pending is not None:
        confirmation = classify_confirmation(current_question, pending)
        if confirmation.decision in {"approve", "edit", "reject"}:
            resolved_proposal = pending
            written = False
            if confirmation.decision == "approve":
                store.write(pending)
                written = True
                confirmation_note = "Saved that HealthCore operational fact for next time."
            elif confirmation.decision == "edit" and confirmation.edited_fact:
                resolved_proposal = MemoryProposal(
                    proposal_id=pending.proposal_id,
                    action="upsert",
                    fact=confirmation.edited_fact,
                    reason="User-edited version of an approved HealthCore memory proposal.",
                    keys=pending.keys,
                )
                if not confirmation.edited_fact.strip():
                    confirmation = confirmation.__class__("reject", reason="empty edit")
                else:
                    store.write(resolved_proposal)
                    written = True
                    confirmation_note = "Saved your edited HealthCore operational fact for next time."
            if confirmation.decision == "reject" or not written:
                confirmation_note = "Okay, I won't store that memory."
            store.audit(
                proposal=resolved_proposal,
                originating_message=pending.fact,
                user_message=current_question,
                decision=confirmation.decision,
                written=written,
                reason=confirmation.reason,
            )
            store.clear_pending(conversation_id)
            current_question = confirmation.remainder
        else:
            store.audit(
                proposal=pending,
                originating_message=pending.fact,
                user_message=current_question,
                decision="reject",
                written=False,
                reason="ambiguous or topic-changing response; rejection is the safe default",
            )
            store.clear_pending(conversation_id)

    if confirmation_note and not current_question:
        result = {
            "question": str(question or "").strip(),
            "route": "memory_confirmation",
            "answer": confirmation_note,
            "final_answer": confirmation_note,
            "error": None,
            "trace_id": run_id,
            "session_id": conversation_id,
            "memory_proposal": None,
            "trace_steps": [
                {
                    "node": "memory_confirmation",
                    "order": 1,
                    "output_summary": "pending proposal resolved",
                }
            ],
        }
        store_guardrail_trace(run_id, result)
        return result

    decision = classify_input(current_question, trace_id=run_id)
    if decision.action != "allow":
        result = {
            "question": current_question,
            "route": "guardrail",
            "route_reason": decision.reason,
            "answer": decision.response,
            "final_answer": decision.response,
            "error": None,
            "trace_id": run_id,
            "session_id": conversation_id,
            "memory_proposal": None,
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
    memory_context = [
        {
            "source": "approved_memory",
            "text": f"Approved HealthCore memory: {entry['fact']}",
            "memory_key": entry["memory_key"],
            "keys": entry["keys"],
        }
        for entry in store.read_relevant(current_question)
    ]
    result = AGENT_GRAPH.invoke(
        {
            "question": current_question,
            "trace_id": run_id,
            "trace_steps": [],
            "memory_context": memory_context,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    safe_answer = (
        None
        if result.get("error") and result.get("answer") is None
        else validate_agent_output(result.get("answer"), trace_id=run_id)
    )
    response = {
        **result,
        "answer": safe_answer,
        "final_answer": safe_answer,
        "trace_id": run_id,
        "session_id": conversation_id,
        "memory_proposal": None,
    }
    if confirmation_note:
        response["answer"] = f"{confirmation_note}\n\n{response['answer']}"
        response["final_answer"] = response["answer"]
    if not result.get("error"):
        proposal = propose_memory(current_question, safe_answer)
        if proposal is not None and store.set_pending(conversation_id, proposal):
            store.audit(
                proposal=proposal,
                originating_message=current_question,
                user_message=current_question,
                decision="proposed",
                written=False,
                reason=proposal.reason,
            )
            response["memory_proposal"] = proposal.as_dict()
            response["answer"] = (
                f"{safe_answer}\n\n"
                "I found a reusable HealthCore operational fact. Would you like me "
                "to remember it for next time? Reply approve, reject, or edit: <your correction>."
            )
            response["final_answer"] = response["answer"]
    return response


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
