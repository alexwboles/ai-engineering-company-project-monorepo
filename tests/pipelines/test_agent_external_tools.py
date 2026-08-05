from __future__ import annotations

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

    def fake_mcp_call(tool_name, arguments):
        calls["tool_name"] = tool_name
        calls["arguments"] = arguments
        return {
            "ok": True,
            "incident": {
                "id": 482,
                "status": "in_progress",
                "category": "access",
                "origin": "support",
                "created_at": "2026-08-04T10:00:00Z",
                "updated_at": "2026-08-04T11:00:00Z",
            },
        }

    monkeypatch.setattr("services.agent.tools.call_mcp_tool", fake_mcp_call)
    result = lookup_ticket(TicketLookupInput(ticket_id=482))

    assert result.found is True
    assert result.ticket_id == 482
    assert result.status == "in_progress"
    assert calls["tool_name"] == "manage_incident_ticket"
    assert calls["arguments"] == {"action": "get_status", "ticket_id": 482}


def test_status_filter_ticket_tool_uses_mcp_filter(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        "services.agent.tools.call_mcp_tool",
        lambda tool_name, arguments: calls.update(tool_name=tool_name, arguments=arguments)
        or {"ok": True, "incidents": [{"id": 482, "status": "open"}]},
    )

    result = lookup_ticket(TicketLookupInput(status="open"))

    assert result.found is True
    assert result.incidents == [{"id": 482, "status": "open"}]
    assert calls == {
        "tool_name": "manage_incident_ticket",
        "arguments": {"action": "get_status", "status": "open"},
    }


def test_inventory_tool_reads_current_stock_and_filters_by_product(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.agent.tools.call_mcp_tool",
        lambda _tool_name, _arguments: {
            "ok": True,
            "products": [
                {"id": 7, "name": "Diagnostic supplies", "sku": "DS-007", "current_stock": 18}
            ],
        },
    )

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
