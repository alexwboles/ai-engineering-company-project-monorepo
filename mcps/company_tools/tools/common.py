"""Shared validation, logging, and response helpers for MCP tools."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastmcp.exceptions import ToolError

from ..auth import authenticated_client_id, require_scope


logger = logging.getLogger("healthcore.mcp")
F = TypeVar("F", bound=Callable[..., Any])


def require_tool_scope(scope: str) -> None:
    try:
        require_scope(scope)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc


def validation_error(message: str) -> ToolError:
    return ToolError(f"VALIDATION_ERROR: {message}")


def log_invocation(tool_name: str, input_summary: dict[str, Any], result: str, started: float) -> None:
    logger.info(
        "mcp_tool_invocation %s",
        json.dumps(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "client_id": authenticated_client_id(),
                "tool": tool_name,
                "input_summary": input_summary,
                "result": result,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
            sort_keys=True,
        ),
    )


def instrument(tool_name: str) -> Callable[[F], F]:
    def decorator(function: F) -> F:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            input_summary = {
                key: value
                for key, value in kwargs.items()
                if key in {"action", "ticket_id", "product_id", "search", "status"}
            }
            result = "success"
            try:
                return function(*args, **kwargs)
            except ToolError as exc:
                result = str(exc).split(":", 1)[0]
                raise
            except Exception:
                result = "error"
                raise
            finally:
                log_invocation(tool_name, input_summary, result, started)

        return wrapper  # type: ignore[return-value]

    return decorator
