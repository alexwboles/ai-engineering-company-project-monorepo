"""Department-scoped human approval, arbitration, and final document workflow.

The public ``interrupt`` and ``resume`` functions are explicit workflow entry
points. SQLite stores the state before an interrupt so a process restart can
resume one department without replaying intake or response generation.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from services.rfp_intake.constants import CONTACT_ROLES, HEALTHCORE_DEPARTMENTS
from services.rfp_intake.models import RfpTicketStatus
from services.rfp_intake.store import RfpTicketStore, default_artifact_dir
from services.rfp_response.loop import MAX_ITERATIONS, run_generator_evaluator_loop

from .checkpointer import ApprovalCheckpointer

ApprovalDecision = Literal["approve", "reject", "request_changes"]
APPROVAL_DECISIONS: tuple[str, ...] = ("approve", "reject", "request_changes")
MAX_APPROVAL_ITERATIONS = MAX_ITERATIONS


class ApprovalWorkflowError(ValueError):
    """Raised when a ticket cannot accept the requested approval transition."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": state["thread_id"],
        "ticket_id": state["ticket_id"],
        "status": state["status"],
        "max_iterations": state["max_iterations"],
        "branches": state["branches"],
        "arbitration": state.get("arbitration"),
        "final_document": state.get("final_document"),
        "updated_at": state.get("updated_at"),
    }


def _trace(
    checkpointer: ApprovalCheckpointer,
    state: dict[str, Any],
    *,
    node: str,
    agent: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> None:
    checkpointer.append_trace(
        thread_id=state["thread_id"],
        ticket_id=state["ticket_id"],
        node=node,
        agent=agent,
        input_data=input_data,
        output_data=output_data,
    )


def _sync_ticket(
    state: dict[str, Any],
    ticket_store: RfpTicketStore,
    *,
    status: RfpTicketStatus,
    final_document: dict[str, Any] | None = None,
) -> None:
    ticket = ticket_store.get(state["ticket_id"])
    if ticket is None:
        raise ApprovalWorkflowError("RFP ticket no longer exists.")
    response = dict(ticket.response or {})
    response["approval_status"] = state["status"]
    response["approval_thread_id"] = state["thread_id"]
    ticket_store.update(
        state["ticket_id"],
        status=status,
        approval=_public_state(state),
        response=response,
        final_document=final_document,
        error=None,
    )


def _approval_payload(state: dict[str, Any], branch: dict[str, Any]) -> dict[str, Any]:
    evaluation = branch.get("evaluation") or {}
    return {
        "ticket_id": state["ticket_id"],
        "thread_id": state["thread_id"],
        "department": branch["department"],
        "approver_role": branch["approver_role"],
        "section_summary": branch["draft"][:700],
        "evaluation_snapshot": {
            "passed": bool(evaluation.get("passed")),
            "iterations": evaluation.get("iterations", branch.get("iterations", 0)),
        },
        "actions": list(APPROVAL_DECISIONS),
    }


def interrupt(
    state: dict[str, Any],
    department: str,
    *,
    checkpointer: ApprovalCheckpointer,
) -> dict[str, Any]:
    """Persist a single department branch before returning its HITL payload."""

    branch = state["branches"].get(department)
    if branch is None:
        raise ApprovalWorkflowError(f"Unknown HealthCore department: {department}.")
    branch["status"] = "awaiting_approval"
    branch["updated_at"] = _now()
    state["status"] = "awaiting_approval"
    state["updated_at"] = _now()
    checkpointer.save_state(state)
    payload = _approval_payload(state, branch)
    _trace(
        checkpointer,
        state,
        node="department_approval_interrupt",
        agent=f"{department} approval gate",
        input_data={"department": department, "branch_status": "ready_for_approval"},
        output_data={"department": department, "status": "awaiting_approval", "actions": list(APPROVAL_DECISIONS)},
    )
    return payload


def start_approval_run(
    ticket_id: str,
    *,
    store: RfpTicketStore | None = None,
    checkpointer: ApprovalCheckpointer | None = None,
) -> dict[str, Any]:
    """Create or return the durable, branch-scoped approval run for a ticket."""

    ticket_store = store or RfpTicketStore()
    checkpoint = checkpointer or ApprovalCheckpointer()
    ticket = ticket_store.get(ticket_id)
    if ticket is None:
        raise ApprovalWorkflowError("RFP ticket not found.")
    if not ticket.response or not isinstance(ticket.response.get("department_tickets"), list):
        raise ApprovalWorkflowError("Department response sections are not ready for approval.")
    existing = ticket.approval or {}
    existing_thread = existing.get("thread_id")
    if existing_thread:
        existing_state = checkpoint.load_state(str(existing_thread))
        if existing_state is not None:
            return _public_state(existing_state)

    workstreams = {
        str(row.get("department")): row
        for row in (ticket.result or {}).get("by_department", [])
        if isinstance(row, dict) and row.get("department")
    }
    department_rows = {
        str(row.get("department")): row
        for row in ticket.response["department_tickets"]
        if isinstance(row, dict) and row.get("department")
    }
    departments = [department for department in HEALTHCORE_DEPARTMENTS if department in department_rows]
    if not departments:
        raise ApprovalWorkflowError("No HealthCore department sections are available for approval.")

    state: dict[str, Any] = {
        "thread_id": f"rfp:{ticket_id}:approval:{uuid4().hex[:10]}",
        "ticket_id": ticket_id,
        "status": "awaiting_approval",
        "max_iterations": MAX_APPROVAL_ITERATIONS,
        "created_at": _now(),
        "updated_at": _now(),
        "metadata": ticket.metadata or {},
        "branches": {},
        "arbitration": None,
        "final_document": None,
    }
    for department in departments:
        row = department_rows[department]
        state["branches"][department] = {
            "department": department,
            "approver_role": CONTACT_ROLES[department],
            "status": "pending",
            "draft": str(row.get("assigned_content") or ""),
            "evaluation": row.get("evaluation") or {},
            "iterations": int(row.get("iterations") or 0),
            "revision_attempts": 0,
            "workstream": workstreams.get(department, {"department": department}),
            "approval": None,
            "feedback": None,
            "updated_at": _now(),
        }

    # The initial checkpoint is written before any branch can interrupt.
    checkpoint.save_state(state)
    _trace(
        checkpoint,
        state,
        node="approval_run_created",
        agent="approval_orchestrator",
        input_data={"ticket_id": ticket_id, "departments": departments},
        output_data={"thread_id": state["thread_id"], "branch_count": len(departments)},
    )
    requests = [interrupt(state, department, checkpointer=checkpoint) for department in departments]
    _sync_ticket(state, ticket_store, status=RfpTicketStatus.AWAITING_APPROVAL)
    public = _public_state(state)
    public["approval_requests"] = requests
    return public


def _detect_conflicts(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect structured contradictions using HealthCore ownership rules."""

    pricing: dict[str, tuple[str, str]] = {}
    for department, branch in state["branches"].items():
        match = re.search(r"PRICING_AMOUNT:\s*([0-9]+(?:\.[0-9]+)?)", branch.get("draft", ""), re.IGNORECASE)
        if match:
            pricing[department] = (match.group(1), branch["draft"])
    values = {value for value, _ in pricing.values()}
    if len(values) > 1:
        return [
            {
                "conflict_id": "pricing-amount-mismatch",
                "departments": list(pricing),
                "rule": "HEALTHCORE_REVENUE_CYCLE_OWNS_PRICING",
                "resolution": "Revenue Cycle and Billing is the source of truth for commercial figures; dependent sections must use its amount.",
            }
        ]
    return []


def arbitrate_disagreements(
    state: dict[str, Any],
    *,
    checkpointer: ApprovalCheckpointer,
) -> dict[str, Any]:
    """Explicitly resolve structured conflicts; agents never vote on disagreements."""

    conflicts = _detect_conflicts(state)
    if conflicts:
        result = {"status": "resolved_by_rule", "conflicts": conflicts, "rule": "HealthCore approval hierarchy"}
    else:
        result = {
            "status": "no_conflicts",
            "conflicts": [],
            "rule": "HealthCore approval hierarchy: each department owns its domain; Revenue Cycle owns commercial figures and Compliance owns data controls.",
        }
    state["arbitration"] = {**result, "at": _now()}
    state["updated_at"] = _now()
    checkpointer.save_state(state)
    _trace(
        checkpointer,
        state,
        node="arbitration",
        agent="healthcore_arbitration_node",
        input_data={"approved_departments": [name for name, branch in state["branches"].items() if branch["status"] == "approved"]},
        output_data=result,
    )
    return result


def _revise_branch(
    state: dict[str, Any],
    branch: dict[str, Any],
    feedback: str,
    *,
    checkpointer: ApprovalCheckpointer,
) -> None:
    branch["revision_attempts"] += 1
    remaining = state["max_iterations"] - branch["revision_attempts"] + 1
    if remaining < 1:
        branch["status"] = "needs_revision"
        branch["feedback"] = feedback
        return
    result = run_generator_evaluator_loop(
        branch["workstream"],
        state.get("metadata", {}),
        max_iterations=remaining,
    )
    branch["draft"] = result.assigned_content
    branch["evaluation"] = result.evaluation
    branch["iterations"] = result.iterations
    branch["feedback"] = feedback
    branch["status"] = "needs_human_review" if result.needs_human_review else "awaiting_approval"
    branch["updated_at"] = _now()
    _trace(
        checkpointer,
        state,
        node="department_revision_generator",
        agent=f"{branch['department']} generator",
        input_data={"department": branch["department"], "feedback": feedback, "remaining_iterations": remaining},
        output_data={"status": branch["status"], "iterations": branch["iterations"], "evaluation_passed": not result.needs_human_review},
    )


def _synthesize_final_document(
    state: dict[str, Any],
    *,
    checkpointer: ApprovalCheckpointer,
    artifact_dir: Path,
) -> dict[str, Any]:
    if not all(branch["status"] == "approved" for branch in state["branches"].values()):
        raise ApprovalWorkflowError("The final document requires approval from every department.")
    if state.get("final_document"):
        return state["final_document"]

    state["status"] = "producing"
    state["updated_at"] = _now()
    checkpointer.save_state(state)
    _trace(
        checkpointer,
        state,
        node="ultimate_document_synthesizer",
        agent="ultimate_document_synthesizer",
        input_data={"department_count": len(state["branches"])},
        output_data={"status": "producing"},
    )
    sections: list[str] = ["# HealthCore Digital Pricing Proposal", "", f"Ticket: {state['ticket_id']}", ""]
    sections.append("## Approved departmental sections")
    for department in HEALTHCORE_DEPARTMENTS:
        branch = state["branches"].get(department)
        if branch is None:
            continue
        sections.extend(["", f"## {department}", branch["draft"], "", f"Approved by: {branch['approval']['actor']} at {branch['approval']['at']}"])
    sections.extend(["", "## Approval trace", f"Approval thread: {state['thread_id']}"])
    content = "\n".join(sections).strip() + "\n"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{state['ticket_id']}-final-proposal.md"
    path.write_text(content, encoding="utf-8")
    final_document = {"filename": path.name, "path": str(path), "generated_at": _now()}
    state["final_document"] = final_document
    state["status"] = "done"
    state["updated_at"] = _now()
    checkpointer.save_state(state)
    _trace(
        checkpointer,
        state,
        node="ultimate_document_synthesizer_completed",
        agent="ultimate_document_synthesizer",
        input_data={"approved_departments": list(state["branches"])},
        output_data={"filename": path.name, "status": "done"},
    )
    return final_document


def resume(
    thread_id: str,
    department: str,
    decision: str,
    *,
    actor: str,
    comment: str | None = None,
    store: RfpTicketStore | None = None,
    checkpointer: ApprovalCheckpointer | None = None,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate a human decision and continue only its department branch."""

    if decision not in APPROVAL_DECISIONS:
        raise ApprovalWorkflowError("Decision must be approve, reject, or request_changes.")
    if decision != "approve" and not (comment and comment.strip()):
        raise ApprovalWorkflowError("A comment explaining the requested change is required.")

    ticket_store = store or RfpTicketStore()
    checkpoint = checkpointer or ApprovalCheckpointer()
    state = checkpoint.load_state(thread_id)
    if state is None:
        raise ApprovalWorkflowError("Approval checkpoint not found; the run cannot be resumed.")
    branch = state["branches"].get(department)
    if branch is None:
        raise ApprovalWorkflowError(f"Unknown HealthCore department: {department}.")
    if branch["status"] == "approved":
        raise ApprovalWorkflowError(f"{department} is already approved.")
    if state["status"] == "done":
        raise ApprovalWorkflowError("This RFP already has a completed final document.")

    _trace(
        checkpoint,
        state,
        node="resume",
        agent="human_approval_resume",
        input_data={"department": department, "decision": decision, "actor": actor},
        output_data={"validated": True},
    )
    if decision == "approve":
        branch["status"] = "approved"
        branch["approval"] = {"decision": decision, "actor": actor, "comment": comment, "at": _now()}
        branch["feedback"] = None
        state["status"] = "partially_approved" if not all(item["status"] == "approved" for item in state["branches"].values()) else "arbitrating"
        state["updated_at"] = _now()
        checkpoint.save_state(state)
        _trace(
            checkpoint,
            state,
            node="department_approval_recorded",
            agent="human_approver",
            input_data={"department": department},
            output_data={"status": "approved"},
        )
        if all(item["status"] == "approved" for item in state["branches"].values()):
            arbitrate_disagreements(state, checkpointer=checkpoint)
            final_document = _synthesize_final_document(
                state,
                checkpointer=checkpoint,
                artifact_dir=artifact_dir or default_artifact_dir(),
            )
            _sync_ticket(state, ticket_store, status=RfpTicketStatus.DONE, final_document=final_document)
        else:
            _sync_ticket(state, ticket_store, status=RfpTicketStatus.PARTIALLY_APPROVED)
    else:
        state["status"] = "needs_revision"
        branch["status"] = "needs_revision"
        branch["approval"] = {"decision": decision, "actor": actor, "comment": comment, "at": _now()}
        _revise_branch(state, branch, comment or "Please revise this department section.", checkpointer=checkpoint)
        state["status"] = "awaiting_approval" if branch["status"] == "awaiting_approval" else "needs_revision"
        state["updated_at"] = _now()
        checkpoint.save_state(state)
        _trace(
            checkpoint,
            state,
            node="department_revision_routed",
            agent="approval_router",
            input_data={"department": department, "decision": decision, "comment": comment},
            output_data={"status": branch["status"], "revision_attempts": branch["revision_attempts"]},
        )
        _sync_ticket(
            state,
            ticket_store,
            status=RfpTicketStatus.AWAITING_APPROVAL if branch["status"] == "awaiting_approval" else RfpTicketStatus.NEEDS_REVISION,
        )
    return _public_state(state)


def get_approval_state(
    ticket_id: str,
    *,
    store: RfpTicketStore | None = None,
    checkpointer: ApprovalCheckpointer | None = None,
) -> dict[str, Any] | None:
    ticket_store = store or RfpTicketStore()
    checkpoint = checkpointer or ApprovalCheckpointer()
    ticket = ticket_store.get(ticket_id)
    if ticket is None:
        return None
    thread_id = (ticket.approval or {}).get("thread_id")
    state = checkpoint.load_state(str(thread_id)) if thread_id else None
    if state is None:
        return ticket.approval
    public = _public_state(state)
    public["trace"] = checkpoint.get_trace(state["thread_id"])
    return public


def read_final_document(ticket_id: str, *, store: RfpTicketStore | None = None) -> tuple[str, str] | None:
    ticket = (store or RfpTicketStore()).get(ticket_id)
    if ticket is None or not ticket.final_document:
        return None
    path = Path(str(ticket.final_document.get("path", "")))
    if not path.is_file():
        return None
    return path.name, path.read_text(encoding="utf-8")
