from __future__ import annotations

from pathlib import Path

from services.rfp_approval.checkpointer import ApprovalCheckpointer
from services.rfp_approval.workflow import (
    MAX_APPROVAL_ITERATIONS,
    arbitrate_disagreements,
    get_approval_state,
    resume,
    start_approval_run,
)
from services.rfp_intake.models import RfpTicketStatus
from services.rfp_intake import pipeline as intake_pipeline
from services.rfp_intake.store import RfpTicketStore
from services.rfp_response.pipeline import process_rfp_response


DEPARTMENTS = ["Clinical Operations", "Revenue Cycle and Billing", "Compliance and Data Governance"]
WORKSTREAMS = {
    department: {
        "department": department,
        "needs": [f"Confirm the {department} requirements."],
        "key_aspects": [f"The RFP requests {department} input."],
        "contact": f"{department} lead",
    }
    for department in DEPARTMENTS
}


def _create_ready_ticket(tmp_path: Path, ticket_id: str = "approval-ticket") -> RfpTicketStore:
    store = RfpTicketStore(tmp_path / f"{ticket_id}.json")
    ticket = store.create(ticket_id=ticket_id, filename="healthcore-rfp.pdf", pdf_path="proposal.pdf", owner_user_id=7)
    department_tickets = [
        {
            "department": department,
            "assigned_content": f"## {department}\nA safe HealthCore draft for review.",
            "evaluation": {"passed": True, "iterations": 1, "results": {"readability": {"passed": True}}},
            "iterations": 1,
            "needs_human_review": False,
        }
        for department in DEPARTMENTS
    ]
    store.update(
        ticket.id,
        status=RfpTicketStatus.READY_FOR_APPROVAL,
        metadata={"client": "Austin Community Health Partners"},
        result={"by_department": list(WORKSTREAMS.values())},
        response={"approval_status": "pending", "ready_for_part_3": True, "department_tickets": department_tickets},
    )
    return store


def test_interrupt_checkpoints_and_resume_only_one_department(tmp_path: Path) -> None:
    store = _create_ready_ticket(tmp_path)
    checkpoint_path = tmp_path / "approval.sqlite3"
    checkpointer = ApprovalCheckpointer(checkpoint_path)

    started = start_approval_run(store.get("approval-ticket").id, store=store, checkpointer=checkpointer)
    thread_id = started["thread_id"]
    resumed = resume(
        thread_id,
        "Clinical Operations",
        "approve",
        actor="marcus.reid@healthcore.example",
        store=store,
        checkpointer=ApprovalCheckpointer(checkpoint_path),
        artifact_dir=tmp_path / "artifacts",
    )

    assert resumed["branches"]["Clinical Operations"]["status"] == "approved"
    assert resumed["branches"]["Revenue Cycle and Billing"]["status"] == "awaiting_approval"
    assert resumed["branches"]["Compliance and Data Governance"]["status"] == "awaiting_approval"
    assert store.get("approval-ticket").status == RfpTicketStatus.PARTIALLY_APPROVED
    trace = checkpointer.get_trace(thread_id)
    assert any(row["node"] == "department_approval_interrupt" for row in trace)
    assert any(row["node"] == "resume" for row in trace)
    assert all(row["agent"] and row["input"] is not None and row["output"] is not None and row["ts"] for row in trace)
    public_state = get_approval_state("approval-ticket", store=store, checkpointer=ApprovalCheckpointer(checkpoint_path))
    assert public_state and public_state["trace"][-1]["node"] == "department_approval_recorded"


def test_final_document_is_created_only_after_every_department_approves(tmp_path: Path) -> None:
    store = _create_ready_ticket(tmp_path, "complete-ticket")
    checkpoint = ApprovalCheckpointer(tmp_path / "complete.sqlite3")
    state = start_approval_run("complete-ticket", store=store, checkpointer=checkpoint)

    for department in DEPARTMENTS:
        state = resume(
            state["thread_id"],
            department,
            "approve",
            actor=f"{department.lower().replace(' ', '.')}@healthcore.example",
            store=store,
            checkpointer=ApprovalCheckpointer(tmp_path / "complete.sqlite3"),
            artifact_dir=tmp_path / "artifacts",
        )

    saved = store.get("complete-ticket")
    assert saved.status == RfpTicketStatus.DONE
    assert saved.final_document is not None
    assert Path(saved.final_document["path"]).is_file()
    content = Path(saved.final_document["path"]).read_text(encoding="utf-8")
    assert "HealthCore Digital Pricing Proposal" in content
    assert all(f"## {department}" in content for department in DEPARTMENTS)


def test_request_changes_routes_back_to_generator_and_enforces_iteration_limit(tmp_path: Path) -> None:
    store = _create_ready_ticket(tmp_path, "revision-ticket")
    checkpoint = ApprovalCheckpointer(tmp_path / "revision.sqlite3")
    state = start_approval_run("revision-ticket", store=store, checkpointer=checkpoint)
    state_data = checkpoint.load_state(state["thread_id"])
    state_data["branches"]["Revenue Cycle and Billing"]["revision_attempts"] = MAX_APPROVAL_ITERATIONS
    checkpoint.save_state(state_data)

    revised = resume(
        state["thread_id"],
        "Revenue Cycle and Billing",
        "request_changes",
        actor="tom.callahan@healthcore.example",
        comment="The commercial assumptions need an approved pricing owner.",
        store=store,
        checkpointer=ApprovalCheckpointer(tmp_path / "revision.sqlite3"),
        artifact_dir=tmp_path / "artifacts",
    )

    assert revised["branches"]["Revenue Cycle and Billing"]["status"] == "needs_revision"
    assert revised["branches"]["Revenue Cycle and Billing"]["revision_attempts"] == MAX_APPROVAL_ITERATIONS + 1
    assert store.get("revision-ticket").status == RfpTicketStatus.NEEDS_REVISION
    assert store.get("revision-ticket").final_document is None


def test_arbitration_node_resolves_structured_pricing_disagreement(tmp_path: Path) -> None:
    store = _create_ready_ticket(tmp_path, "arbitration-ticket")
    checkpoint = ApprovalCheckpointer(tmp_path / "arbitration.sqlite3")
    state = start_approval_run("arbitration-ticket", store=store, checkpointer=checkpoint)
    persisted = checkpoint.load_state(state["thread_id"])
    persisted["branches"]["Clinical Operations"]["draft"] += "\nPRICING_AMOUNT: 100"
    persisted["branches"]["Revenue Cycle and Billing"]["draft"] += "\nPRICING_AMOUNT: 200"
    checkpoint.save_state(persisted)

    result = arbitrate_disagreements(persisted, checkpointer=checkpoint)

    assert result["status"] == "resolved_by_rule"
    assert result["conflicts"][0]["rule"] == "HEALTHCORE_REVENUE_CYCLE_OWNS_PRICING"
    assert checkpoint.get_trace(state["thread_id"])[-1]["node"] == "arbitration"


def test_intake_generation_and_approval_share_one_ticket_to_done(tmp_path: Path, monkeypatch) -> None:
    store = RfpTicketStore(tmp_path / "e2e.json")
    pdf_path = tmp_path / "healthcore-rfp.pdf"
    pdf_path.write_bytes(b"placeholder")
    ticket = store.create(ticket_id="e2e-ticket", filename="healthcore-rfp.pdf", pdf_path=str(pdf_path), owner_user_id=7)
    markdown = """# HealthCore Digital Request for Proposal
Client: Austin Community Health Partners
Submission deadline: 2026-09-30
## Scope and requirements
The proposal must integrate clinical EHR and appointment booking systems.
## Compliance and Data Governance
The solution must satisfy HIPAA and UK GDPR data retention requirements.
## Pricing and commercial response
Include implementation pricing, budget assumptions, and support fees.
"""

    def fake_convert(_pdf_path, markdown_path):
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8")
        return markdown

    monkeypatch.setattr(intake_pipeline, "convert_pdf_to_markdown", fake_convert)
    monkeypatch.setattr(intake_pipeline, "default_artifact_dir", lambda: tmp_path / "artifacts")
    intake_pipeline.process_rfp_ticket(ticket.id, store=store)
    process_rfp_response(ticket.id, store=store)

    checkpoint = ApprovalCheckpointer(tmp_path / "e2e.sqlite3")
    state = start_approval_run(ticket.id, store=store, checkpointer=checkpoint)
    for department in list(state["branches"]):
        state = resume(
            state["thread_id"],
            department,
            "approve",
            actor=f"{department} approver",
            store=store,
            checkpointer=ApprovalCheckpointer(tmp_path / "e2e.sqlite3"),
            artifact_dir=tmp_path / "artifacts",
        )

    saved = store.get(ticket.id)
    assert saved.status == RfpTicketStatus.DONE
    assert saved.final_document is not None
    assert saved.approval is not None
    assert "approval_thread_id" in saved.response
