"""Authenticated ticket-mode RFP intake endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

try:
    from services.api.auth_security import get_current_user
    from services.rfp_intake.pipeline import process_rfp_ticket
    from services.rfp_intake.store import RfpTicketStore, default_artifact_dir
except ModuleNotFoundError:
    from auth_security import get_current_user
    from rfp_intake.pipeline import process_rfp_ticket
    from rfp_intake.store import RfpTicketStore, default_artifact_dir


router = APIRouter(prefix="/rfp", tags=["rfp-intake"])
ticket_store = RfpTicketStore()


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


@router.get("/tickets")
def list_rfp_tickets(current_user: Any = Depends(get_current_user)) -> list[dict[str, Any]]:
    return [ticket.model_dump(mode="json") for ticket in ticket_store.list(getattr(current_user, "id", None))]


@router.get("/tickets/{ticket_id}")
def get_rfp_ticket(ticket_id: str, current_user: Any = Depends(get_current_user)) -> dict[str, Any]:
    ticket = ticket_store.get(ticket_id)
    if ticket is None or ticket.owner_user_id != getattr(current_user, "id", None):
        raise HTTPException(status_code=404, detail="RFP ticket not found.")
    return ticket.model_dump(mode="json")
