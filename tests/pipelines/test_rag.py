from __future__ import annotations

from data.pipelines import rag


def _point(point_id: str, text: str) -> tuple[list[float], dict[str, object]]:
    return (
        [1.0, 0.0],
        {
            "source_document": "fixture.md",
            "section": "Fixture policy",
            "company": "HealthCore",
            "language": "en",
            "chunk_index": 0,
            "text": text,
        },
    )


def test_retrieve_filters_below_threshold_and_can_return_fewer_than_k(monkeypatch) -> None:
    monkeypatch.setattr(
        rag,
        "_local_points",
        {
            "relevant": _point("relevant", "HealthCore requires HIPAA review for patient data."),
            "unrelated": _point("unrelated", "The clinic has a Monday operations meeting."),
        },
    )
    monkeypatch.setattr(rag, "_qdrant_client_instance", None)
    monkeypatch.setattr(rag, "_qdrant_unavailable", True)

    results = rag.retrieve("What requires HIPAA review?", k=5, min_score=0.30)

    assert len(results) == 1
    assert results[0]["source_document"] == "fixture.md"
    assert results[0]["score"] >= 0.30


def test_query_delegates_retrieval_and_returns_generation_output(monkeypatch) -> None:
    context = [{"text": "HealthCore protects patient data under HIPAA."}]
    calls: dict[str, object] = {}

    def fake_retrieve(question: str, **kwargs):
        calls["question"] = question
        calls["kwargs"] = kwargs
        return context

    def fake_generate(question: str, retrieved):
        calls["context"] = retrieved
        return "The model-generated answer is grounded in HIPAA policy."

    monkeypatch.setattr(rag, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag, "generate_answer", fake_generate)

    answer = rag.query("How is patient data protected?")

    assert answer == "The model-generated answer is grounded in HIPAA policy."
    assert calls["question"] == "How is patient data protected?"
    assert calls["context"] == context


def test_setup_uses_deterministic_ids_and_required_payload_allowlist(monkeypatch) -> None:
    chunks = [
        {
            "source_document": "fixture.md",
            "section": "Billing",
            "company": "HealthCore",
            "language": "en",
            "chunk_index": 0,
            "text": "A claim must have a positive amount.",
        }
    ]
    monkeypatch.setattr(rag, "build_healthcore_chunks", lambda: chunks)
    monkeypatch.setattr(rag, "embed", lambda _text: [0.5, 0.5])
    monkeypatch.setattr(rag, "_local_points", {})
    monkeypatch.setattr(rag, "_get_qdrant_client", lambda: None)
    monkeypatch.setattr(rag, "_qdrant_unavailable", False)

    first = rag.setup()
    second = rag.setup()

    assert first[0]["id"] == second[0]["id"]
    assert set(chunks[0]) == {
        "source_document",
        "section",
        "company",
        "language",
        "chunk_index",
        "text",
    }
