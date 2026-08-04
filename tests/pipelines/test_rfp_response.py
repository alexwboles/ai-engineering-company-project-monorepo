from services.rfp_response.evaluators.guidelines import evaluate_guidelines
from services.rfp_response.generators.revenue_cycle_billing import RevenueCycleBillingGenerator
from services.rfp_response.loop import run_generator_evaluator_loop
from services.rfp_response.pipeline import process_rfp_response
from services.rfp_intake.store import RfpTicketStore
from services.rfp_intake.models import RfpTicketStatus


WORKSTREAM = {
    "department": "Revenue Cycle and Billing",
    "needs": ["Confirm payer requirements and implementation pricing before submission."],
    "key_aspects": ["The RFP requests a commercial response."],
    "contact": "Revenue Cycle and Billing lead - Tom Callahan",
    "evidence_sections": ["Pricing and commercial response"],
}


def test_department_generator_produces_a_healthcore_pricing_section() -> None:
    draft = RevenueCycleBillingGenerator().generate(WORKSTREAM, {"client": "Austin Community Health Partners"})

    assert "Revenue Cycle and Billing" in draft
    assert "### Pricing and commercial assumptions" in draft
    assert "[TBD" in draft
    assert "HIPAA" in draft and "UK GDPR" in draft


def test_guideline_evaluator_returns_concrete_rule_ids_for_bad_draft() -> None:
    result = evaluate_guidelines(
        "### Pricing\nWe guarantee 99.99% uptime for patient ID HC-A3F291.",
        WORKSTREAM,
    )

    assert result.passed is False
    assert "HC_GUIDELINE_NO_PATIENT_DATA" in result.failed_rules
    assert "HC_GUIDELINE_NO_INVENTED_COMMERCIALS" in result.failed_rules
    assert result.feedback and "HIPAA" in result.feedback


class RetryOnceGenerator:
    def __init__(self) -> None:
        self.calls = 0
        self.real_generator = RevenueCycleBillingGenerator()

    def generate(self, workstream, metadata, feedback):
        self.calls += 1
        if self.calls == 1:
            return "This draft does not answer the assigned request."
        return self.real_generator.generate(workstream, metadata, feedback)


def test_failed_evaluation_returns_feedback_to_generator_and_recovers() -> None:
    generator = RetryOnceGenerator()
    result = run_generator_evaluator_loop(WORKSTREAM, {"client": "Acme"}, generator=generator, max_iterations=3)

    assert generator.calls == 2
    assert result.needs_human_review is False
    assert result.iterations == 2
    assert result.evaluation["passed"] is True


class AlwaysFailingGenerator:
    def generate(self, _workstream, _metadata, _feedback):
        return "Unrelated draft."


def test_iteration_limit_preserves_failed_section_for_human_review() -> None:
    result = run_generator_evaluator_loop(WORKSTREAM, {}, generator=AlwaysFailingGenerator(), max_iterations=2)

    assert result.needs_human_review is True
    assert result.iterations == 2
    assert result.evaluation["passed"] is False
    assert result.evaluation["results"]["relevance"]["feedback"]


def test_response_pipeline_persists_department_handoff_and_status_history(tmp_path) -> None:
    store = RfpTicketStore(tmp_path / "tickets.json")
    ticket = store.create(ticket_id="response-ticket", filename="proposal.pdf", pdf_path="proposal.pdf", owner_user_id=7)
    store.update(
        ticket.id,
        status=RfpTicketStatus.DONE,
        metadata={"client": "Austin Community Health Partners"},
        result={"by_department": [WORKSTREAM]},
    )

    process_rfp_response(ticket.id, store=store)
    saved = store.get(ticket.id)

    assert saved is not None
    assert saved.status == "ready_for_approval"
    assert saved.response is not None
    assert saved.response["ready_for_part_3"] is True
    assert saved.response["department_tickets"][0]["assigned_content"]
    assert saved.response["department_tickets"][0]["evaluation"]["passed"] is True
    assert [entry["status"] for entry in saved.status_history] == ["analyzing", "done", "drafting", "under_evaluation", "ready_for_approval"]
