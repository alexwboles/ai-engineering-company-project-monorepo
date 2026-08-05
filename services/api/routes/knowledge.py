"""HTTP adapter for the HealthCore knowledge-base pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

try:
    from data.pipelines.rag import query
except ModuleNotFoundError:
    from pipelines.rag import query


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.post("/query")
def query_knowledge(payload: KnowledgeQueryRequest) -> dict[str, str]:
    """Return only the model-generated answer, never raw vector results."""

    try:
        answer = query(payload.question.strip())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The HealthCore knowledge assistant could not answer this question. Please try again.",
        ) from None
    return {"answer": answer}
