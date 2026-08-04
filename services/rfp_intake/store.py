"""TinyDB persistence for RFP ticket state and pipeline artifacts."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB

from .models import RfpTicket, RfpTicketStatus


def default_ticket_db_path() -> Path:
    configured = os.getenv("RFP_TICKETS_DB_PATH")
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "services" / "api" / "data" / "rfp_tickets.json"


def default_artifact_dir() -> Path:
    configured = os.getenv("RFP_ARTIFACT_DIR")
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "services" / "api" / "data" / "rfp_intake"


class RfpTicketStore:
    """Small request-safe store; the database is opened for each operation."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_ticket_db_path()
        self._lock = threading.RLock()

    def create(self, *, ticket_id: str, filename: str, pdf_path: str, owner_user_id: int | None) -> RfpTicket:
        now = datetime.now(timezone.utc)
        ticket = RfpTicket(
            id=ticket_id,
            filename=filename,
            pdf_path=pdf_path,
            status=RfpTicketStatus.ANALYZING,
            created_at=now,
            updated_at=now,
            status_history=[{"status": RfpTicketStatus.ANALYZING, "at": now.isoformat()}],
            owner_user_id=owner_user_id,
        )
        self._write(ticket)
        return ticket

    def get(self, ticket_id: str) -> RfpTicket | None:
        with self._lock:
            with TinyDB(self.db_path, indent=2, ensure_ascii=True) as db:
                row = db.table("rfp_tickets").get(Query().id == ticket_id)
        return RfpTicket.model_validate(row) if row else None

    def list(self, owner_user_id: int | None = None) -> list[RfpTicket]:
        with self._lock:
            with TinyDB(self.db_path, indent=2, ensure_ascii=True) as db:
                rows = db.table("rfp_tickets").all()
        tickets = [RfpTicket.model_validate(row) for row in rows]
        if owner_user_id is not None:
            tickets = [ticket for ticket in tickets if ticket.owner_user_id == owner_user_id]
        return sorted(tickets, key=lambda ticket: ticket.created_at, reverse=True)

    def update(self, ticket_id: str, **changes: Any) -> RfpTicket:
        ticket = self.get(ticket_id)
        if ticket is None:
            raise KeyError(f"RFP ticket {ticket_id} does not exist")

        previous_status = ticket.status
        for key, value in changes.items():
            setattr(ticket, key, value)
        ticket.updated_at = datetime.now(timezone.utc)
        if "status" in changes and changes["status"] != previous_status:
            ticket.status_history.append({"status": str(changes["status"]), "at": ticket.updated_at.isoformat()})
        self._write(ticket)
        return ticket

    def _write(self, ticket: RfpTicket) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with TinyDB(self.db_path, indent=2, ensure_ascii=True) as db:
                table = db.table("rfp_tickets")
                if table.get(Query().id == ticket.id):
                    table.update(ticket.model_dump(mode="json"), Query().id == ticket.id)
                else:
                    table.insert(ticket.model_dump(mode="json"))
