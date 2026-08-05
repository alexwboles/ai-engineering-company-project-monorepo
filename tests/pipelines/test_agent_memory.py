from __future__ import annotations

from pathlib import Path

import pytest

from services.agent import nodes
from services.agent.graph import invoke_agent
from services.agent.memory.confirm import classify_confirmation
from services.agent.memory.models import MemoryProposal
from services.agent.memory.policy import propose_memory
from services.agent.memory.store import MemoryPolicyError, MemoryStore


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "healthcore-memory.sqlite3")


@pytest.fixture
def fake_generation(monkeypatch):
    observed: list[list[dict[str, object]]] = []
    monkeypatch.setattr(nodes, "retrieve", lambda _question: [{"text": "HealthCore fixture context."}])

    def generate(_question: str, context: list[dict[str, object]]) -> str:
        observed.append(context)
        return "HealthCore operational answer."

    monkeypatch.setattr(nodes, "generate_answer", generate)
    return observed


def test_approved_cycle_writes_and_reuses_memory(tmp_path: Path, fake_generation) -> None:
    store = _store(tmp_path)
    session = "approved-cycle"
    correction = "Correction: HealthCore's no-show reminder workflow uses two calls before the appointment."

    proposed = invoke_agent(correction, session_id=session, trace_id="approved-proposal", memory_store=store)

    assert proposed["memory_proposal"]["fact"] == "HealthCore's no-show reminder workflow uses two calls before the appointment"
    assert store.list() == []
    assert proposed["answer"].endswith("Reply approve, reject, or edit: <your correction>.")

    approved = invoke_agent(
        "approve and what is HealthCore's no-show reminder workflow?",
        session_id=session,
        trace_id="approved-confirmation",
        memory_store=store,
    )

    assert approved["memory_proposal"] is None
    assert "Saved" in approved["answer"]
    assert "HealthCore operational answer." in approved["answer"]
    assert len(store.list()) == 1
    assert [row["decision"] for row in store.audit_entries()] == ["proposed", "approve"]

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(nodes, "retrieve", lambda _question: [])
        reused = invoke_agent(
            "What is HealthCore's no-show reminder workflow?",
            session_id=session,
            trace_id="approved-reuse",
            memory_store=store,
        )
    finally:
        monkeypatch.undo()

    assert reused["answer"] == "HealthCore operational answer."
    assert any("two calls" in str(item["text"]) for item in fake_generation[-1])


def test_rejected_cycle_keeps_memory_unchanged(tmp_path: Path, fake_generation) -> None:
    store = _store(tmp_path)
    session = "rejected-cycle"
    correction = "Actually, HealthCore claim denials should be reviewed by Revenue Cycle and Billing before resubmission."

    proposed = invoke_agent(correction, session_id=session, trace_id="rejected-proposal", memory_store=store)
    assert proposed["memory_proposal"] is not None

    rejected = invoke_agent("no", session_id=session, trace_id="rejected-confirmation", memory_store=store)

    assert "won't store" in rejected["answer"]
    assert store.list() == []
    assert store.audit_entries()[-1]["decision"] == "reject"
    assert store.audit_entries()[-1]["written"] == 0


def test_ambiguous_topic_change_discards_pending_then_continues(tmp_path: Path, fake_generation) -> None:
    store = _store(tmp_path)
    session = "ambiguous-cycle"
    invoke_agent(
        "Remember that HealthCore's inventory reconciliation runs every Friday.",
        session_id=session,
        trace_id="ambiguous-proposal",
        memory_store=store,
    )

    result = invoke_agent(
        "What is HealthCore's claim denial rate?",
        session_id=session,
        trace_id="ambiguous-topic",
        memory_store=store,
    )

    assert result["route"] == "rag"
    assert store.list() == []
    assert store.audit_entries()[-1]["reason"].startswith("ambiguous")


def test_only_one_pending_proposal_is_allowed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = MemoryProposal("mem-1", "upsert", "HealthCore workflow correction one", "test", ("policy",))
    second = MemoryProposal("mem-2", "upsert", "HealthCore workflow correction two", "test", ("policy",))

    assert store.set_pending("one-pending", first) is True
    assert store.set_pending("one-pending", second) is False
    assert store.get_pending("one-pending").proposal_id == "mem-1"


def test_confirmation_requires_a_classified_intent() -> None:
    proposal = MemoryProposal("mem-1", "upsert", "HealthCore policy correction", "test", ("policy",))

    assert classify_confirmation("sounds good", proposal).decision == "unclear"
    assert classify_confirmation("approve", proposal).decision == "approve"
    assert classify_confirmation("edit: HealthCore policy changed", proposal).decision == "edit"


def test_policy_dismisses_non_memorable_and_forbidden_examples() -> None:
    assert propose_memory("What is the HealthCore claim denial rate?", "14%.") is None
    assert propose_memory("Thanks for your help with HealthCore.", "You're welcome.") is None
    assert propose_memory(
        "Correction: patient HC-ABC123's appointment was moved.",
        "I understand.",
    ) is None


def test_forbidden_memory_cannot_be_written_even_if_constructed_directly(tmp_path: Path) -> None:
    store = _store(tmp_path)
    forbidden = MemoryProposal(
        "mem-forbidden",
        "upsert",
        "HealthCore patient HC-ABC123 diagnosis detail",
        "test",
        ("patient",),
    )

    with pytest.raises(MemoryPolicyError):
        store.write(forbidden)


def test_cleanup_expires_entries(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "short-lived.sqlite3", ttl_days=0)
    proposal = MemoryProposal("mem-expiring", "upsert", "HealthCore policy correction", "test", ("policy",))

    store.write(proposal)

    assert store.list() == []
