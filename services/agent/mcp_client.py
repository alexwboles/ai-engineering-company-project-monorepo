"""LangChain MCP client adapter used by the support-agent graph."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient


MCP_SERVER_NAME = "company_tools"


def _connection_config() -> dict[str, dict[str, Any]]:
    transport = os.getenv("MCP_TRANSPORT", "streamable_http")
    if transport == "stdio":
        return {
            MCP_SERVER_NAME: {
                "transport": "stdio",
                "command": os.getenv("MCP_STDIO_COMMAND", "uv"),
                "args": ["run", "python", "-m", "mcps.company_tools.server"],
                "cwd": str(Path(__file__).resolve().parents[2]),
                "env": {
                    "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                    "MCP_TRANSPORT": "stdio",
                    "MCP_ACCESS_TOKEN": os.getenv("MCP_ACCESS_TOKEN", ""),
                    "MCP_JWT_SECRET": os.getenv("MCP_JWT_SECRET", ""),
                },
            }
        }

    token = os.getenv("MCP_ACCESS_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return {
        MCP_SERVER_NAME: {
            "transport": "streamable_http",
            "url": os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"),
            "headers": headers,
            "timeout": float(os.getenv("MCP_CLIENT_TIMEOUT_SECONDS", "10.0")),
        }
    }


async def _invoke_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    client = MultiServerMCPClient(
        _connection_config(),
        tool_name_prefix=True,
        handle_tool_errors=True,
    )
    tools = await client.get_tools(server_name=MCP_SERVER_NAME)
    tool = next(
        (
            candidate
            for candidate in tools
            if candidate.name == tool_name
            or candidate.name.endswith(f"_{tool_name}")
        ),
        None,
    )
    if tool is None:
        return {
            "ok": False,
            "error_code": "MCP_TOOL_NOT_FOUND",
            "message": f"MCP tool {tool_name} was not discovered.",
        }
    result = await tool.ainvoke(arguments)
    return _normalize_result(result)


def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a discovered MCP tool from the synchronous LangGraph node."""

    try:
        return asyncio.run(_invoke_mcp_tool(tool_name, arguments))
    except Exception as exc:
        return {
            "ok": False,
            "error_code": "MCP_CLIENT_ERROR",
            "message": "The MCP company-tools server could not be reached.",
            "detail": str(exc),
        }


def _normalize_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    content = getattr(result, "content", result)
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        content = "".join(text_parts) or content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {"ok": False, "error_code": "MCP_INVALID_RESPONSE", "message": content}
        return parsed if isinstance(parsed, dict) else {"ok": True, "data": parsed}
    return {"ok": False, "error_code": "MCP_INVALID_RESPONSE", "message": "Unexpected MCP response."}
