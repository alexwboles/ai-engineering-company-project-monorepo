from __future__ import annotations

import httpx

from services.agent import nodes
from services.agent.graph import invoke_agent
from services.agent.tools import (
    InventoryLookupInput,
    TicketLookupInput,
    TicketLookupOutput,
    lookup_inventory,
    lookup_ticket,
)


def test_ticket_tool_uses_real_incident_route_and_explicit_timeout(monkeypatch) -> None:
    calls: dict[str, object] = {}
    request = httpx.Request("GET", "http://incident-manager/api/incidents/482")
    response = httpx.Response(
        200,
        json={
            "id": 482,
            "status": "in_progress",
            "category": "access",
            "origin": "support",
            "created_at": "2026-08-04T10:00:00Z",
            "updated_at": "2026-08-04T11:00:00Z",
        },
        request=request,
    )

    def fake_get(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return response

    monkeypatch.setattr("services.agent.tools.httpx.get", fake_get)
    result = lookup_ticket(TicketLookupInput(ticket_id=482))

    assert result.found is True
    assert result.ticket_id == 482
    assert result.status == "in_progress"
    assert calls["url"] == "http://localhost:8000/api/incidents/482"
    assert calls["timeout"] == 4.0


def test_inventory_tool_reads_current_stock_and_filters_by_product(monkeypatch) -> None:
    request = httpx.Request("GET", "http://inventory-manager/inventory/products")
    response = httpx.Response(
        200,
        json=[{"id": 7, "name": "Diagnostic supplies", "sku": "DS-007", "current_stock": 18}],
        request=request,
    )
    monkeypatch.setattr("services.agent.tools.httpx.get", lambda _url, **_kwargs: response)

    result = lookup_inventory(InventoryLookupInput(search="diagnostic"))

    assert result.found is True
    assert result.products[0].current_stock == 18


def test_ticket_question_routes_to_tool_without_running_rag(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "retrieve", lambda _question: (_ for _ in ()).throw(AssertionError("RAG ran")))
    monkeypatch.setattr(
        nodes,
        "lookup_ticket",
        lambda _request: TicketLookupOutput(
            found=True,
            ticket_id=482,
            status="in_progress",
            category="access",
            source="support",
        ),
    )
    monkeypatch.setattr(nodes, "generate_answer", lambda _question, context: f"live result: {context[0]['text']}")

    result = invoke_agent("What is the status of ticket 482?", trace_id="eval-ticket-tool")
    trace_nodes = [step["node"] for step in result["trace_steps"]]

    assert result["route"] == "ticket"
    assert trace_nodes == ["receive_question", "route_intent", "lookup_ticket", "synthesize_answer"]
    assert result["tool_results"][0]["outcome"] == "success"
    assert "in_progress" in result["answer"]


def test_policy_question_routes_to_rag_without_running_tools(monkeypatch) -> None:
    monkeypatch.setattr(nodes, "lookup_ticket", lambda _request: (_ for _ in ()).throw(AssertionError("ticket ran")))
    monkeypatch.setattr(nodes, "lookup_inventory", lambda _request: (_ for _ in ()).throw(AssertionError("inventory ran")))
    monkeypatch.setattr(nodes, "retrieve", lambda _question: [{"text": "HealthCore policy context."}])
    monkeypatch.setattr(nodes, "generate_answer", lambda _question, _context: "grounded policy answer")

    result = invoke_agent("What rules protect patient data in the UK?", trace_id="eval-rag-routing")
    trace_nodes = [step["node"] for step in result["trace_steps"]]

    assert result["route"] == "rag"
    assert trace_nodes == ["receive_question", "route_intent", "retrieve", "query"]
    assert result.get("tool_results", []) == []
    assert result["answer"] == "grounded policy answer"


def test_ticket_timeout_uses_honest_fallback_without_fabricated_status(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "lookup_ticket",
        lambda _request: TicketLookupOutput(found=False, error="timeout", outcome="timeout"),
    )

    result = invoke_agent("What is the status of ticket 482?", trace_id="eval-ticket-fallback")
    trace_nodes = [step["node"] for step in result["trace_steps"]]

    assert trace_nodes[-1] == "handle_tool_failure"
    assert "couldn't confirm" in result["answer"]
    assert "in_progress" not in result["answer"]
