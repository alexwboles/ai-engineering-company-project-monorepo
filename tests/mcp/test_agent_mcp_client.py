from __future__ import annotations

from services.agent import mcp_client


def test_agent_invokes_discovered_tool_through_langchain_mcp_adapter(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeTool:
        name = "company_tools_manage_incident_ticket"

        async def ainvoke(self, arguments):
            calls.append((self.name, arguments))
            return {"ok": True, "incident": {"id": 482, "status": "open"}}

    class FakeClient:
        def __init__(self, connections, **kwargs):
            assert connections["company_tools"]["transport"] == "streamable_http"
            assert kwargs["tool_name_prefix"] is True

        async def get_tools(self, *, server_name):
            assert server_name == "company_tools"
            return [FakeTool()]

    monkeypatch.setattr(mcp_client, "MultiServerMCPClient", FakeClient)

    result = mcp_client.call_mcp_tool(
        "manage_incident_ticket",
        {"action": "get_status", "ticket_id": 482},
    )

    assert result["ok"] is True
    assert calls == [
        (
            "company_tools_manage_incident_ticket",
            {"action": "get_status", "ticket_id": 482},
        )
    ]
