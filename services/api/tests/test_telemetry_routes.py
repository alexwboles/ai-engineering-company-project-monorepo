from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.main import app
from services.api.telemetry_storage import InMemoryTelemetryStore, SupabaseTelemetryStore


def valid_event(event_id: str = "event-1") -> dict[str, Any]:
    return {
        "eventId": event_id,
        "timestamp": "2026-08-03T21:00:00.000Z",
        "sessionId": "session-1",
        "userId": None,
        "event_type": "claim_submitted",
        "schemaVersion": "1.0.0",
        "requestId": "request-1",
        "properties": {
            "claimId": "CLM-000001",
            "locationId": "us-tx-001",
            "payerId": "payer-1",
            "payerName": "Health Plan",
            "serviceType": "primary_care",
            "claimAmount": 200,
            "resubmitted": False,
            "submissionChannel": "backoffice_snapshot",
        },
    }


def test_mixed_batch_persists_valid_events_and_rejects_only_invalid_events() -> None:
    store = InMemoryTelemetryStore()
    app.state.telemetry_store = store

    invalid_event = valid_event("event-2")
    invalid_event.pop("requestId")

    with TestClient(app) as client:
        response = client.post("/telemetry/events", json={"events": [valid_event(), invalid_event]})

    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 1}
    assert len(store.rows) == 1
    assert store.bulk_insert_calls == 1
    assert store.rows[0]["event_id"] == "event-1"
    assert store.rows[0]["event_type"] == "claim_submitted"
    assert store.rows[0]["tags"]["claimId"] == "CLM-000001"


def test_non_object_event_is_rejected_without_canceling_the_batch() -> None:
    store = InMemoryTelemetryStore()
    app.state.telemetry_store = store

    with TestClient(app) as client:
        response = client.post("/telemetry/events", json={"events": ["malformed", valid_event()]})

    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 1}
    assert len(store.rows) == 1
    assert store.bulk_insert_calls == 1


def test_empty_batch_is_accepted_without_a_storage_call() -> None:
    store = InMemoryTelemetryStore()
    app.state.telemetry_store = store

    with TestClient(app) as client:
        response = client.post("/telemetry/events", json={"events": []})

    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
    assert store.rows == []
    assert store.bulk_insert_calls == 0


def test_envelope_errors_are_rejected_before_the_handler_runs() -> None:
    with TestClient(app) as client:
        response = client.post("/telemetry/events", json={"not_events": []})

    assert response.status_code == 422


def test_supabase_store_sends_one_post_for_the_whole_batch(monkeypatch) -> None:
    class StubResponse:
        def raise_for_status(self) -> None:
            return None

    class StubClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, endpoint: str, *, headers: dict[str, str], json: list[dict[str, Any]]) -> StubResponse:
            self.calls.append({"endpoint": endpoint, "headers": headers, "json": json})
            return StubResponse()

    client = StubClient()
    monkeypatch.setattr("services.api.telemetry_storage.httpx.AsyncClient", lambda **_kwargs: client)
    store = SupabaseTelemetryStore("https://example.supabase.co", "server-key")
    rows = [{"event_id": "event-1"}, {"event_id": "event-2"}]

    import asyncio

    asyncio.run(store.bulk_insert(rows))

    assert len(client.calls) == 1
    assert client.calls[0]["endpoint"] == "https://example.supabase.co/rest/v1/telemetry_events"
    assert client.calls[0]["json"] == rows
    assert client.calls[0]["headers"]["Authorization"] == "Bearer server-key"
