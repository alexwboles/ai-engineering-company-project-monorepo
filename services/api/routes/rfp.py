"""Authenticated ticket-mode RFP intake endpoints."""

from __future__ import annotations

import asyncio
import json
import queue
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

try:
    from services.api.auth_security import get_current_user
    from services.realtime_notifications import Notification, notification_broker
    from services.rfp_intake.pipeline import process_rfp_ticket
    from services.rfp_intake.store import RfpTicketStore, default_artifact_dir
    from services.rfp_response.pipeline import process_rfp_response
    from services.rfp_approval import ApprovalWorkflowError, get_approval_state, read_final_document, resume, start_approval_run
except ModuleNotFoundError:
    from auth_security import get_current_user
    from realtime_notifications import Notification, notification_broker
    from rfp_intake.pipeline import process_rfp_ticket
    from rfp_intake.store import RfpTicketStore, default_artifact_dir
    from rfp_response.pipeline import process_rfp_response
    from rfp_approval import ApprovalWorkflowError, get_approval_state, read_final_document, resume, start_approval_run


router = APIRouter(prefix="/rfp", tags=["rfp-intake"])
ticket_store = RfpTicketStore()


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_changes"]
    comment: str | None = Field(default=None, max_length=2000)


def format_sse(notification: Notification) -> str:
    """Serialize one named notification using the SSE wire format."""

    encoded_data = json.dumps(notification.payload, separators=(",", ":"), ensure_ascii=True)
    return f"id: {notification.event_id}\nevent: {notification.event_name}\ndata: {encoded_data}\n\n"


async def _notification_stream(request: Request, *, user_id: int) -> Any:
    subscriber_id, subscriber_queue = notification_broker.subscribe(
        user_id=user_id,
        last_event_id=request.headers.get("last-event-id"),
    )
    try:
        yield ": connected\n\n"
        while not await request.is_disconnected():
            try:
                notification = await asyncio.to_thread(subscriber_queue.get, True, 15)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            yield format_sse(notification)
    finally:
        notification_broker.unsubscribe(subscriber_id)


@router.post("/tickets", status_code=status.HTTP_202_ACCEPTED)
async def create_rfp_ticket(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload an RFP PDF file.")

    ticket_id = uuid.uuid4().hex
    artifact_dir = default_artifact_dir()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = artifact_dir / f"{ticket_id}.pdf"
    try:
        with pdf_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                destination.write(chunk)
    except OSError:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Unable to stage the RFP PDF. Please try again.") from None
    finally:
        await file.close()

    if pdf_path.stat().st_size == 0:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded RFP PDF is empty.")

    ticket = ticket_store.create(
        ticket_id=ticket_id,
        filename=filename,
        pdf_path=str(pdf_path),
        owner_user_id=getattr(current_user, "id", None),
    )
    background_tasks.add_task(process_rfp_ticket, ticket.id)
    return ticket.model_dump(mode="json")


@router.get("/tickets/stream")
async def stream_rfp_ticket_notifications(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> StreamingResponse:
    """Stream ticket-created and ticket-status events to an authenticated dashboard."""

    return StreamingResponse(
        _notification_stream(request, user_id=int(getattr(current_user, "id"))),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tickets")
def list_rfp_tickets(current_user: Any = Depends(get_current_user)) -> list[dict[str, Any]]:
    return [ticket.model_dump(mode="json") for ticket in ticket_store.list(getattr(current_user, "id", None))]


@router.get("/tickets/{ticket_id}")
def get_rfp_ticket(ticket_id: str, current_user: Any = Depends(get_current_user)) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    return ticket.model_dump(mode="json")


@router.post("/tickets/{ticket_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_rfp_response(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    if ticket.status not in {"done", "needs_human_review", "failed"}:
        return ticket.model_dump(mode="json")

    background_tasks.add_task(process_rfp_response, ticket.id)
    return ticket.model_dump(mode="json")


@router.post("/tickets/{ticket_id}/approvals/start", status_code=status.HTTP_202_ACCEPTED)
def start_rfp_approvals(ticket_id: str, current_user: Any = Depends(get_current_user)) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    try:
        return start_approval_run(ticket_id, store=ticket_store)
    except ApprovalWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/tickets/{ticket_id}/approvals")
def get_rfp_approvals(ticket_id: str, current_user: Any = Depends(get_current_user)) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    approval = get_approval_state(ticket_id, store=ticket_store)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval run has not started.")
    return approval


@router.post("/tickets/{ticket_id}/approvals/{department}")
def resume_rfp_approval(
    ticket_id: str,
    department: str,
    payload: ApprovalDecisionRequest,
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    thread_id = (ticket.approval or {}).get("thread_id")
    if not thread_id:
        raise HTTPException(status_code=409, detail="Start the approval run before submitting a decision.")
    try:
        return resume(
            str(thread_id),
            department,
            payload.decision,
            actor=str(getattr(current_user, "email", getattr(current_user, "id", "authenticated approver"))),
            comment=payload.comment,
            store=ticket_store,
        )
    except ApprovalWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/tickets/{ticket_id}/final-document")
def get_final_rfp_document(ticket_id: str, current_user: Any = Depends(get_current_user)) -> dict[str, str]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    document = read_final_document(ticket_id, store=ticket_store)
    if document is None:
        raise HTTPException(status_code=404, detail="The final proposal is not available yet.")
    filename, content = document
    return {"filename": filename, "content": content}
