"""RFP intake pipeline: convert, triage, orchestrate, work, and synthesize."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .agents.classifier import classify_rfp
from .agents.orchestrator import build_workstreams
from .agents.synthesizer import synthesize_rfp
from .agents.workers import run_department_worker
from .convert import convert_pdf_to_markdown
from .metrics import compute_readability, extract_metadata
from .models import RfpTicketStatus
from .store import RfpTicketStore, default_artifact_dir

logger = logging.getLogger("healthcore.rfp_intake")


def process_rfp_ticket(ticket_id: str, *, store: RfpTicketStore | None = None) -> None:
    ticket_store = store or RfpTicketStore()
    ticket = ticket_store.get(ticket_id)
    if ticket is None:
        logger.error("RFP ticket not found: ticket_id=%s", ticket_id)
        return

    try:
        ticket_store.update(ticket_id, status=RfpTicketStatus.ANALYZING)
        pdf_path = Path(ticket.pdf_path)
        markdown_path = default_artifact_dir() / f"{ticket_id}.md"
        markdown = convert_pdf_to_markdown(pdf_path, markdown_path)
        metadata = extract_metadata(markdown)
        readability = compute_readability(markdown)
        classification = classify_rfp(markdown)
        ticket_store.update(
            ticket_id,
            markdown_path=str(markdown_path),
            metadata=metadata,
            readability=readability,
            classifier=classification.as_dict(),
        )

        if not classification.is_rfp:
            ticket_store.update(ticket_id, status=RfpTicketStatus.DISCARDED, error=classification.reason)
            logger.info("RFP ticket discarded: ticket_id=%s reason=%s", ticket_id, classification.reason)
            return

        workstreams = build_workstreams(markdown, classification.detected_departments, classification.unknown_departments)
        ticket_store.update(ticket_id, status=RfpTicketStatus.WAITING_FOR_APPROVAL)
        # Workers are independent and only receive their assigned section slice.
        with ThreadPoolExecutor(max_workers=max(1, len(workstreams))) as executor:
            worker_results = list(executor.map(run_department_worker, workstreams))
        result = synthesize_rfp(
            metadata=metadata,
            readability=readability,
            worker_results=worker_results,
            unknown_departments=classification.unknown_departments,
        )
        ticket_store.update(ticket_id, result=result, status=RfpTicketStatus.DONE)
        logger.info("RFP ticket completed: ticket_id=%s workstreams=%s", ticket_id, len(worker_results))
    except Exception as exc:
        logger.exception("RFP ticket failed: ticket_id=%s", ticket_id)
        try:
            ticket_store.update(ticket_id, status=RfpTicketStatus.FAILED, error="RFP analysis failed. Please retry the ticket.")
        except Exception:
            logger.exception("Unable to persist failed RFP ticket state: ticket_id=%s", ticket_id)
