"""Part 2 response pipeline consuming the completed Part 1 ticket summary."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from services.rfp_intake.models import RfpTicketStatus
from services.rfp_intake.store import RfpTicketStore

from .loop import MAX_ITERATIONS, run_generator_evaluator_loop

logger = logging.getLogger("healthcore.rfp_response")


def process_rfp_response(
    ticket_id: str,
    *,
    store: RfpTicketStore | None = None,
    max_iterations: int = MAX_ITERATIONS,
) -> None:
    ticket_store = store or RfpTicketStore()
    ticket = ticket_store.get(ticket_id)
    if ticket is None:
        logger.error("RFP response ticket not found: ticket_id=%s", ticket_id)
        return
    if not ticket.result or not isinstance(ticket.result.get("by_department"), list):
        ticket_store.update(ticket_id, status=RfpTicketStatus.FAILED, error="RFP intake summary is not ready for response generation.")
        return

    try:
        ticket_store.update(ticket_id, status=RfpTicketStatus.DRAFTING)
        workstreams = [row for row in ticket.result["by_department"] if isinstance(row, dict) and row.get("department")]
        ticket_store.update(ticket_id, status=RfpTicketStatus.UNDER_EVALUATION)
        metadata = ticket.metadata or {}
        with ThreadPoolExecutor(max_workers=max(1, len(workstreams))) as executor:
            section_results = list(
                executor.map(
                    lambda workstream: run_generator_evaluator_loop(
                        workstream,
                        metadata,
                        max_iterations=max_iterations,
                    ),
                    workstreams,
                )
            )

        department_tickets = [result.as_dict() for result in section_results]
        requires_review = any(result.needs_human_review for result in section_results)
        handoff: dict[str, Any] = {
            "source_ticket_id": ticket_id,
            "approval_status": "pending",
            "ready_for_part_3": not requires_review,
            "department_tickets": department_tickets,
        }
        final_status = RfpTicketStatus.NEEDS_HUMAN_REVIEW if requires_review else RfpTicketStatus.READY_FOR_APPROVAL
        ticket_store.update(ticket_id, response=handoff, status=final_status, error=None)
        logger.info("RFP response completed: ticket_id=%s review_required=%s", ticket_id, requires_review)
    except Exception:
        logger.exception("RFP response generation failed: ticket_id=%s", ticket_id)
        ticket_store.update(ticket_id, status=RfpTicketStatus.FAILED, error="RFP response generation failed. Please retry.")
