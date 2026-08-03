from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

logger = logging.getLogger("healthcore.telemetry.storage")


class TelemetryStorageError(RuntimeError):
    """Raised when the telemetry persistence service cannot accept a batch."""


class TelemetryQueryError(RuntimeError):
    """Raised when the telemetry read path cannot load a report window."""


class TelemetryStore(Protocol):
    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        """Persist all rows in one operation."""

    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Load only the events needed for a report window."""


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

    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, str]] = [
            ("select", "timestamp,event_type,tags"),
            ("timestamp", f"gte.{_as_utc_iso(start_date)}"),
            ("timestamp", f"lt.{_as_utc_iso(end_date)}"),
            ("order", "timestamp.asc"),
        ]
        if event_types:
            params.append(("event_type", f"in.({','.join(event_types)})"))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
            raise TelemetryQueryError("Unable to load telemetry for the requested report window") from exc

        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise TelemetryQueryError("Telemetry query returned an unexpected shape")
        return payload


class InMemoryTelemetryStore:
    """Safe local fallback used when Supabase settings are absent in development."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.bulk_insert_calls = 0

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        self.bulk_insert_calls += 1
        self.rows.extend(rows)

    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        allowed_types = set(event_types) if event_types else None
        result: list[dict[str, Any]] = []
        for row in self.rows:
            timestamp = _parse_timestamp(row.get("timestamp"))
            if timestamp is None or not (start_date <= timestamp < end_date):
                continue
            if allowed_types is not None and row.get("event_type") not in allowed_types:
                continue
            result.append(row)
        return result


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


def _as_utc_iso(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
