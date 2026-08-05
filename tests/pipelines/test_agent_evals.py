from __future__ import annotations

from data.pipelines.rag import query, retrieve
from services.agent.graph import get_agent_trace, invoke_agent


def test_agent_trace_records_retrieve_before_query(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.agent.nodes.retrieve",
        lambda _question: [{"id": "fixture", "source": "fixture", "text": "HealthCore uses HIPAA." , "score": 1.0}],
    )
    monkeypatch.setattr("services.agent.nodes.generate_answer", lambda _question, context: f"grounded: {context[0]['text']}")

    result = invoke_agent("Which policy applies?", trace_id="eval-node-order")
    nodes = [step["node"] for step in result["trace_steps"]]

    assert nodes == ["receive_question", "route_intent", "retrieve", "query"]
    assert get_agent_trace("eval-node-order")["trace"] == result["trace_steps"]


def test_grounded_answer_uses_healthcore_knowledge_base() -> None:
    result = invoke_agent("What laws protect HealthCore patient data?", trace_id="eval-grounded")

    assert "HIPAA" in result["answer"]
    assert "UK GDPR" in result["answer"]
    assert result["error"] is None


def test_empty_question_ends_without_query_node() -> None:
    result = invoke_agent("", trace_id="eval-empty")
    nodes = [step["node"] for step in result["trace_steps"]]

    assert nodes == ["receive_question"]
    assert result["answer"] is None
    assert result["error"] == "Question cannot be empty."


def test_retrieve_and_query_keep_the_existing_generation_contract() -> None:
    context = retrieve("What is the HealthCore claim denial rate?")

    assert context
    assert "14%" in query("What is the HealthCore claim denial rate?", context)
