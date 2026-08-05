"""Single-responsibility nodes for the HealthCore support graph."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from data.pipelines.rag import generate_answer, retrieve

from .state import AgentState, TraceStep
from .tools import (
    InventoryLookupInput,
    TicketLookupInput,
    lookup_inventory,
    lookup_ticket,
)


logger = logging.getLogger("healthcore.agent")


def _trace(state: AgentState, node: str, summary: str) -> TraceStep:
    previous = state.get("trace_steps") or []
    return {"node": node, "order": len(previous) + 1, "output_summary": summary}


def receive_question(state: AgentState) -> dict[str, Any]:
    question = str(state.get("question") or "").strip()
    if not question:
        return {
            "question": question,
            "answer": None,
            "final_answer": None,
            "error": "Question cannot be empty.",
            "trace_steps": [_trace(state, "receive_question", "empty question; graph will end")],
        }
    return {
        "question": question,
        "error": None,
        "trace_steps": [_trace(state, "receive_question", "question accepted")],
    }


def route_intent(state: AgentState) -> dict[str, Any]:
    """Choose live tools, RAG, or both from the question without user flags."""

    question = state["question"]
    lowered = question.casefold()
    ticket_requested = any(
        term in lowered for term in ("ticket", "incident", "support case", "support issue")
    )
    inventory_requested = any(term in lowered for term in ("inventory", "stock", "product", "sku"))

    if ticket_requested and inventory_requested:
        route = "both"
        tools = ["ticket", "inventory"]
    elif ticket_requested:
        route = "ticket"
        tools = ["ticket"]
    elif inventory_requested:
        route = "inventory"
        tools = ["inventory"]
    else:
        route = "rag"
        tools = []

    reason = (
        f"matched live sources: {', '.join(tools) or 'none'}; "
        "defaulted to HealthCore knowledge base"
        if route == "rag"
        else f"matched live sources: {', '.join(tools)}"
    )
    return {
        "route": route,
        "route_reason": reason,
        "requested_tools": tools,
        "trace_steps": [
            _trace(state, "route_intent", f"source=router route={route}; {reason}")
        ],
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    question = state["question"]
    try:
        context = retrieve(question)
    except Exception:
        logger.exception("Support-agent retrieval failed: trace_id=%s", state.get("trace_id"))
        return {
            "error": "Agent failed during retrieval. Check the trace for this run.",
            "trace_steps": [_trace(state, "retrieve", "source=rag outcome=error")],
        }
    return {
        "retrieved_context": context,
        "trace_steps": [
            _trace(state, "retrieve", f"source=rag outcome=success chunks={len(context)}")
        ],
    }


def lookup_ticket_node(state: AgentState) -> dict[str, Any]:
    request = TicketLookupInput(
        ticket_id=_ticket_id(state["question"]),
        status=_ticket_status(state["question"]),
    )
    result = lookup_ticket(request)
    result_data = {"tool": "ticket", **result.model_dump()}
    outcome = str(result_data.get("outcome", "success"))
    return {
        "tool_results": [*(state.get("tool_results") or []), result_data],
        "trace_steps": [
            _trace(state, "lookup_ticket", f"source=incident_manager outcome={outcome}")
        ],
    }


def lookup_inventory_node(state: AgentState) -> dict[str, Any]:
    request = InventoryLookupInput(search=_inventory_search(state["question"]))
    result = lookup_inventory(request)
    result_data = {"tool": "inventory", **result.model_dump()}
    outcome = str(result_data.get("outcome", "success"))
    return {
        "tool_results": [*(state.get("tool_results") or []), result_data],
        "trace_steps": [
            _trace(state, "lookup_inventory", f"source=inventory_manager outcome={outcome}")
        ],
    }


def no_context_node(state: AgentState) -> dict[str, Any]:
    answer = "I don't have information about that in the HealthCore knowledge base."
    return {
        "answer": answer,
        "final_answer": answer,
        "trace_steps": [_trace(state, "no_context", "source=rag outcome=no_context")],
    }


def tool_failure_node(state: AgentState) -> dict[str, Any]:
    failures = [item for item in state.get("tool_results", []) if item.get("error")]
    tools = {str(item.get("tool")) for item in failures}
    if "ticket" in tools:
        answer = "I couldn't confirm that ticket's status right now. The incident manager did not return a reliable result."
    elif "inventory" in tools:
        answer = "I couldn't confirm current inventory right now. The inventory manager did not return a reliable result."
    else:
        answer = "I couldn't confirm the live operational data right now. Please try again later."
    return {
        "answer": answer,
        "final_answer": answer,
        "trace_steps": [
            _trace(
                state,
                "handle_tool_failure",
                f"source=tool outcome=fallback failed={','.join(sorted(tools))}",
            )
        ],
    }


def query_node(state: AgentState) -> dict[str, Any]:
    try:
        answer = generate_answer(state["question"], state.get("retrieved_context") or [])
    except Exception:
        logger.exception("Support-agent generation failed: trace_id=%s", state.get("trace_id"))
        return {
            "error": "Agent failed while generating an answer. Check the trace for this run.",
            "trace_steps": [_trace(state, "query", "source=rag outcome=generation_error")],
        }
    return {
        "answer": answer,
        "final_answer": answer,
        "trace_steps": [_trace(state, "query", "source=rag outcome=success")],
    }


def synthesize_answer_node(state: AgentState) -> dict[str, Any]:
    """Generate from live tool results and optional RAG context after routing."""

    tool_context = [
        {"text": _tool_context(item), "source": item.get("tool", "tool")}
        for item in state.get("tool_results", [])
        if not item.get("error")
    ]
    context = [*(state.get("retrieved_context") or []), *tool_context]
    try:
        answer = generate_answer(state["question"], context)
    except Exception:
        logger.exception("Support-agent synthesis failed: trace_id=%s", state.get("trace_id"))
        return {
            "error": "Agent failed while synthesizing live data. Check the trace for this run.",
        "trace_steps": [
            _trace(state, "synthesize_answer", "source=rag+tools outcome=generation_error")
        ],
        }
    return {
        "answer": answer,
        "final_answer": answer,
        "trace_steps": [_trace(state, "synthesize_answer", "source=tools+rag outcome=success")],
    }


def _ticket_id(question: str) -> int | None:
    match = re.search(
        r"(?:ticket|incident|case)\s*#?\s*(\d+)", question, flags=re.IGNORECASE
    )
    return int(match.group(1)) if match else None


def _ticket_status(question: str) -> str | None:
    for status in ("open", "in_progress", "resolved", "closed"):
        if status.replace("_", " ") in question.casefold() or status in question.casefold():
            return status
    return None


def _inventory_search(question: str) -> str | None:
    match = re.search(
        r"(?:stock|inventory)\s+(?:of|for)\s+([a-z0-9 _-]+)",
        question,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip(" ?.") if match else None


def _tool_context(item: dict[str, Any]) -> str:
    tool = item.get("tool")
    clean = {
        key: value
        for key, value in item.items()
        if key not in {"tool", "outcome", "error"} and value not in (None, [])
    }
    return f"Live {tool} manager result: {json.dumps(clean, sort_keys=True)}"
