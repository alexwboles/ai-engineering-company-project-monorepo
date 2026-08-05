"""Thin API adapter for the compiled HealthCore support-agent graph."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

try:
    from services.agent.graph import get_agent_trace, invoke_agent
    from services.agent.harness.observability import guardrail_summary
except ModuleNotFoundError:
    from agent.graph import get_agent_trace, invoke_agent
    from agent.harness.observability import guardrail_summary


router = APIRouter(prefix="/agent", tags=["support-agent"])


class AgentQueryRequest(BaseModel):
    question: str = ""
    session_id: str | None = None


@router.post("/query")
def query_agent(payload: AgentQueryRequest) -> dict[str, Any]:
    trace_id = None
    try:
        result = invoke_agent(payload.question, session_id=payload.session_id)
        trace_id = result["trace_id"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The support agent could not complete this request. Please try again.",
        ) from None

    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{result['error']} Trace: {trace_id}",
        )
    return {
        "answer": result.get("answer", ""),
        "trace_id": trace_id,
        "session_id": result.get("session_id"),
        "memory_proposal": result.get("memory_proposal"),
    }


@router.get("/traces/{trace_id}")
def get_agent_run_trace(trace_id: str) -> dict[str, Any]:
    trace = get_agent_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent trace not found.")
    return trace


@router.get("/guardrails/summary")
def get_guardrail_summary() -> dict[str, int]:
    """Expose process-local guardrail counts for a test or operations session."""

    return guardrail_summary()
