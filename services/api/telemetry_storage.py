from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any, Protocol

import httpx

logger = logging.getLogger("healthcore.telemetry.storage")


class TelemetryStorageError(RuntimeError):
    """Raised when the telemetry persistence service cannot accept a batch."""


class TelemetryStore(Protocol):
    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        """Persist all rows in one operation."""


class SupabaseTelemetryStore:
    def __init__(self, supabase_url: str, api_key: str, table_name: str = "telemetry_events") -> None:
        self.endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
        self.headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.endpoint, headers=self.headers, json=rows)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise TelemetryStorageError("Supabase telemetry insert failed") from exc


class InMemoryTelemetryStore:
    """Safe local fallback used when Supabase settings are absent in development."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.bulk_insert_calls = 0

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        self.bulk_insert_calls += 1
        self.rows.extend(rows)


def create_telemetry_store(env: Mapping[str, str] | None = None) -> TelemetryStore:
    settings = env if env is not None else os.environ
    supabase_url = settings.get("SUPABASE_URL", "").strip()
    api_key = settings.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    table_name = settings.get("SUPABASE_TELEMETRY_TABLE", "telemetry_events").strip() or "telemetry_events"

    if supabase_url and api_key:
        return SupabaseTelemetryStore(supabase_url, api_key, table_name)

    logger.warning("Supabase telemetry settings are absent; using in-memory storage for local development")
    return InMemoryTelemetryStore()


def event_to_storage_row(event: Any) -> dict[str, Any]:
    return {
        "event_id": event.eventId,
        "timestamp": event.timestamp,
        "session_id": event.sessionId,
        "user_id": event.userId,
        "event_type": event.event_type,
        "schema_version": event.schemaVersion,
        "request_id": event.requestId,
        "tags": event.properties,
    }
