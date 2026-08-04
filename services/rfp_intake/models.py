"""Serializable models for the ticket-mode RFP workflow."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RfpTicketStatus(StrEnum):
    ANALYZING = "analyzing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    DONE = "done"
    DISCARDED = "discarded"
    FAILED = "failed"


class RfpTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    pdf_path: str
    markdown_path: str | None = None
    status: RfpTicketStatus
    created_at: datetime
    updated_at: datetime
    status_history: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    readability: dict[str, Any] | None = None
    classifier: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    owner_user_id: int | None = None
