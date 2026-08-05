"""HTTP adapter for the existing HealthCore services."""

from __future__ import annotations

import os
from typing import Any

import httpx


class UpstreamError(Exception):
    """A safe, structured failure returned by an existing HealthCore service."""

    def __init__(self, error_code: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def request_upstream(
    method: str,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    timeout = float(os.getenv("MCP_UPSTREAM_TIMEOUT_SECONDS", "4.0"))
    token = os.getenv("MCP_UPSTREAM_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise UpstreamError("UPSTREAM_TIMEOUT", "The HealthCore service did not respond in time.") from exc
    except httpx.HTTPError as exc:
        raise UpstreamError("UPSTREAM_UNAVAILABLE", "The HealthCore service is unavailable.") from exc

    if response.status_code == 401 or response.status_code == 403:
        raise UpstreamError("UPSTREAM_AUTH_REQUIRED", "The upstream service rejected its service token.", response.status_code)
    if response.status_code == 404:
        raise UpstreamError("UPSTREAM_NOT_FOUND", "The requested HealthCore record was not found.", response.status_code)
    if response.is_error:
        raise UpstreamError("UPSTREAM_HTTP_ERROR", f"The upstream service returned HTTP {response.status_code}.", response.status_code)
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamError("UPSTREAM_INVALID_RESPONSE", "The upstream service returned invalid JSON.") from exc
    if not isinstance(payload, (dict, list)):
        raise UpstreamError("UPSTREAM_INVALID_RESPONSE", "The upstream service returned an unexpected response shape.")
    return payload
