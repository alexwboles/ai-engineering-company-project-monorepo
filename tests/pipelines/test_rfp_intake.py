from services.rfp_intake.agents.classifier import classify_rfp
from services.rfp_intake.agents.orchestrator import build_workstreams
from services.rfp_intake.agents.workers.department_worker import DepartmentWorker
from services.rfp_intake import pipeline
from services.rfp_intake.store import RfpTicketStore


VALID_HEALTHCORE_RFP = """
# HealthCore Digital Request for Proposal
Client: Austin Community Health Partners
Submission deadline: 2026-09-30
## Scope and requirements
The proposal must provide an integration with the clinical EHR and appointment booking systems.
## Compliance and Data Governance
The solution must satisfy HIPAA and UK GDPR data retention requirements.
## Pricing and commercial response
Include implementation pricing, budget assumptions, and support fees.
"""


def test_classifier_accepts_a_healthcore_rfp_with_required_signals() -> None:
    result = classify_rfp(VALID_HEALTHCORE_RFP)

    assert result.is_rfp is True
    assert "Compliance and Data Governance" in result.detected_departments
    assert "Technology" in result.detected_departments
    assert result.unknown_departments == []


def test_classifier_discards_a_document_that_is_not_an_rfp() -> None:
    result = classify_rfp("# HealthCore brochure\nLearn about our clinics and services.")

    assert result.is_rfp is False
    assert "missing" in result.reason.lower()


def test_classifier_keeps_rfp_like_document_discarded_when_commercial_signal_is_missing() -> None:
    result = classify_rfp(
        "# Request for Proposal\nSubmission deadline: 2026-09-30\n## Scope\nIntegrate the clinical EHR."
    )

    assert result.is_rfp is False


def test_department_worker_uses_only_orchestrated_slice() -> None:
    workstreams = build_workstreams(VALID_HEALTHCORE_RFP, ["Compliance and Data Governance"])
    result = DepartmentWorker().run(workstreams[0])

    assert result.department == "Compliance and Data Governance"
    assert any("HIPAA" in aspect for aspect in result.key_aspects)
    assert result.suggested_contact_role.startswith("Compliance and Data Governance lead")
    assert all("clinical EHR" not in aspect for aspect in result.key_aspects)


def test_valid_ticket_records_analysis_history_and_done_result(tmp_path, monkeypatch) -> None:
    store = RfpTicketStore(tmp_path / "tickets.json")
    pdf_path = tmp_path / "proposal.pdf"
    pdf_path.write_bytes(b"placeholder")
    ticket = store.create(ticket_id="ticket-1", filename="proposal.pdf", pdf_path=str(pdf_path), owner_user_id=7)

    def fake_convert(_pdf_path, markdown_path):
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(VALID_HEALTHCORE_RFP, encoding="utf-8")
        return VALID_HEALTHCORE_RFP

    monkeypatch.setattr(pipeline, "convert_pdf_to_markdown", fake_convert)
    monkeypatch.setattr(pipeline, "default_artifact_dir", lambda: tmp_path / "artifacts")

    pipeline.process_rfp_ticket(ticket.id, store=store)
    saved = store.get(ticket.id)

    assert saved is not None
    assert saved.status == "done"
    assert [entry["status"] for entry in saved.status_history] == ["analyzing", "waiting_for_approval", "done"]
    assert saved.metadata is not None
    assert saved.readability is not None
    assert saved.result is not None


def test_non_rfp_ticket_is_explicitly_discarded(tmp_path, monkeypatch) -> None:
    store = RfpTicketStore(tmp_path / "tickets.json")
    pdf_path = tmp_path / "brochure.pdf"
    pdf_path.write_bytes(b"placeholder")
    ticket = store.create(ticket_id="ticket-2", filename="brochure.pdf", pdf_path=str(pdf_path), owner_user_id=7)

    monkeypatch.setattr(pipeline, "convert_pdf_to_markdown", lambda _pdf_path, _markdown_path: "# HealthCore brochure\nOur clinics.")
    monkeypatch.setattr(pipeline, "default_artifact_dir", lambda: tmp_path / "artifacts")

    pipeline.process_rfp_ticket(ticket.id, store=store)
    saved = store.get(ticket.id)

    assert saved is not None
    assert saved.status == "discarded"
    assert saved.error and "missing" in saved.error.lower()
    assert [entry["status"] for entry in saved.status_history] == ["analyzing", "discarded"]
