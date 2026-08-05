"""Task status endpoints backed by the Celery result backend."""

from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter

from services.celery_app import celery_app


router = APIRouter(tags=["tasks"])
STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str) -> dict[str, object]:
    result = AsyncResult(task_id, app=celery_app)
    status = STATUS_MAP.get(result.status, "pending")
    payload: dict[str, object] = {"task_id": task_id, "status": status, "result": None}

    if status == "success":
        payload["result"] = result.result
    elif status == "failure":
        payload["result"] = str(result.result)

    return payload
