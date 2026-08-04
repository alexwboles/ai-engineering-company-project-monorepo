"""Single-responsibility nodes for the HealthCore support graph."""

from __future__ import annotations

import logging
from typing import Any

from data.pipelines.rag import generate_answer, retrieve

from .state import AgentState, TraceStep

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
            "error": "Question cannot be empty.",
            "trace_steps": [_trace(state, "receive_question", "empty question; graph will end")],
        }
    return {
        "question": question,
        "error": None,
        "trace_steps": [_trace(state, "receive_question", "question accepted")],
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    question = state["question"]
    try:
        context = retrieve(question)
    except Exception:
        logger.exception("Support-agent retrieval failed: trace_id=%s", state.get("trace_id"))
        return {
            "error": "Agent failed during retrieval. Check the trace for this run.",
            "trace_steps": [_trace(state, "retrieve", "retrieval failed")],
        }
    return {
        "retrieved_context": context,
        "trace_steps": [_trace(state, "retrieve", f"retrieved {len(context)} context chunks")],
    }


def no_context_node(state: AgentState) -> dict[str, Any]:
    answer = "I don't have information about that in the HealthCore knowledge base."
    return {
        "answer": answer,
        "trace_steps": [_trace(state, "no_context", "returned an honest no-context answer")],
    }


def query_node(state: AgentState) -> dict[str, Any]:
    try:
        answer = generate_answer(state["question"], state.get("retrieved_context") or [])
    except Exception:
        logger.exception("Support-agent generation failed: trace_id=%s", state.get("trace_id"))
        return {
            "error": "Agent failed while generating an answer. Check the trace for this run.",
            "trace_steps": [_trace(state, "query", "answer generation failed")],
        }
    return {
        "answer": answer,
        "trace_steps": [_trace(state, "query", "generated answer from retrieved context")],
    }
