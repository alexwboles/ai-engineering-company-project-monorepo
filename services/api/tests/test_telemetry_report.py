from __future__ import annotations

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from services.api.main import app
from services.api.routes.telemetry_report import clear_report_cache
from services.api.telemetry_storage import InMemoryTelemetryStore
from services.telemetry.analysis import (
    auth_failure_rate,
    error_rate_by_type,
    events_per_day,
    latency_by_route,
)


def telemetry_row(
    event_id: str,
    timestamp: str,
    event_type: str,
    tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "session_id": "report-session",
        "user_id": None,
        "event_type": event_type,
        "schema_version": "1.0.0",
        "request_id": f"request-{event_id}",
        "tags": tags or {},
    }


def report_store() -> InMemoryTelemetryStore:
    store = InMemoryTelemetryStore()
    store.rows.extend(
        [
            telemetry_row("1", "2026-08-01T01:00:00Z", "claim_submitted"),
            telemetry_row("2", "2026-08-01T02:00:00Z", "frontend_error_occurred"),
            telemetry_row("3", "2026-08-01T03:00:00Z", "auth_login_attempted"),
            telemetry_row("4", "2026-08-01T04:00:00Z", "auth_login_failed"),
            telemetry_row(
                "5",
                "2026-08-02T04:00:00Z",
                "api_latency_recorded",
                {"route": "/telemetry/report", "durationMs": 42},
            ),
        ]
    )
    return store


def test_metrics_group_by_utc_date_and_return_serialisable_records() -> None:
    store = report_store()
    start = _date("2026-08-01T00:00:00Z")
    end = _date("2026-08-03T00:00:00Z")

    daily = asyncio.run(events_per_day(store, start, end))
    errors = asyncio.run(error_rate_by_type(store, start, end))
    latency = asyncio.run(latency_by_route(store, start, end))
    auth = asyncio.run(auth_failure_rate(store, start, end))

    assert daily == [{"date": "2026-08-01", "event_count": 4}, {"date": "2026-08-02", "event_count": 1}]
    assert errors == [
        {
            "date": "2026-08-01",
            "event_type": "auth_login_failed",
            "error_count": 1,
            "total_events": 4,
            "error_rate_percent": 25.0,
        },
        {
            "date": "2026-08-01",
            "event_type": "frontend_error_occurred",
            "error_count": 1,
            "total_events": 4,
            "error_rate_percent": 25.0,
        }
    ]
    assert latency[0]["route"] == "/telemetry/report"
    assert latency[0]["average_duration_ms"] == 42.0
    assert auth == [
        {
            "date": "2026-08-01",
            "total_login_attempts": 2,
            "failed_login_attempts": 1,
            "failure_rate_percent": 50.0,
        }
    ]


def test_report_returns_all_metrics_and_caches_same_window(monkeypatch) -> None:
    store = report_store()
    app.state.telemetry_store = store
    app.state.telemetry_reader = store
    clear_report_cache()
    calls = 0

    async def fake_pipeline(reader, start_date, end_date):
        nonlocal calls
        calls += 1
        assert reader is store
        assert start_date.isoformat() == "2026-08-01T00:00:00+00:00"
        assert end_date.isoformat() == "2026-08-03T00:00:00+00:00"
        return {"events_per_day": [], "event_volume_by_type": [], "error_rate_by_type": [], "latency_by_route": [], "auth_failure_rate": []}

    monkeypatch.setattr("services.api.routes.telemetry_report.calculate_technical_report", fake_pipeline)

    with TestClient(app) as client:
        first = client.get(
            "/telemetry/report",
            params={"start_date": "2026-08-01T00:00:00Z", "end_date": "2026-08-03T00:00:00Z"},
        )
        second = client.get(
            "/telemetry/report",
            params={"start_date": "2026-08-01T00:00:00Z", "end_date": "2026-08-03T00:00:00Z"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["period"] == {"from": "2026-08-01T00:00:00Z", "to": "2026-08-03T00:00:00Z"}
    assert set(first.json()["metrics"]) == {
        "events_per_day",
        "event_volume_by_type",
        "error_rate_by_type",
        "latency_by_route",
        "auth_failure_rate",
    }
    assert calls == 1


def test_report_rejects_invalid_dates_and_reversed_windows() -> None:
    clear_report_cache()
    with TestClient(app) as client:
        invalid = client.get("/telemetry/report", params={"start_date": "not-a-date"})
        reversed_window = client.get(
            "/telemetry/report",
            params={"start_date": "2026-08-03", "end_date": "2026-08-01"},
        )

    assert invalid.status_code == 400
    assert reversed_window.status_code == 400


def _date(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
