from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from queue import Empty
from types import SimpleNamespace

from services.api.routes.rfp import format_sse, stream_rfp_ticket_notifications
from services.realtime_notifications import notification_broker, publish_rfp_ticket_created
from services.rfp_intake.store import RfpTicketStore
from starlette.requests import Request


def setup_function() -> None:
    notification_broker.reset_for_tests()


def teardown_function() -> None:
    notification_broker.reset_for_tests()


def test_rfp_ticket_creation_emits_named_structured_sse_event(tmp_path) -> None:
    subscriber_id, subscriber_queue = notification_broker.subscribe(user_id=7)
    store = RfpTicketStore(tmp_path / "tickets.json")

    ticket = store.create(
        ticket_id="rfp-123",
        filename="healthcore-rfp.pdf",
        pdf_path=str(tmp_path / "rfp-123.pdf"),
        owner_user_id=7,
    )

    notification = subscriber_queue.get(timeout=1)
    notification_broker.unsubscribe(subscriber_id)
    assert notification.event_name == "rfp_ticket_created"
    assert notification.payload["ticket_id"] == ticket.id
    assert notification.payload["status"] == "analyzing"

    wire_payload = format_sse(notification)
    assert f"id: {notification.event_id}" in wire_payload
    assert "event: rfp_ticket_created" in wire_payload
    assert '"ticket_id":"rfp-123"' in wire_payload
    assert '"status":"analyzing"' in wire_payload


def test_reconnect_replays_only_events_after_last_event_id() -> None:
    first = publish_rfp_ticket_created(
        ticket_id="rfp-first",
        status="analyzing",
        created_at=datetime.now(timezone.utc),
        user_id=11,
    )
    subscriber_id, subscriber_queue = notification_broker.subscribe(user_id=11, last_event_id=first.event_id)
    try:
        try:
            subscriber_queue.get_nowait()
        except Empty:
            pass
        else:
            raise AssertionError("the reconnect replayed an already received event")

        second = publish_rfp_ticket_created(
            ticket_id="rfp-second",
            status="analyzing",
            created_at=datetime.now(timezone.utc),
            user_id=11,
        )
        replayed = subscriber_queue.get(timeout=1)
        assert replayed.event_id == second.event_id
        assert replayed.payload["ticket_id"] == "rfp-second"
    finally:
        notification_broker.unsubscribe(subscriber_id)


def test_events_are_scoped_to_the_authenticated_ticket_owner() -> None:
    subscriber_id, subscriber_queue = notification_broker.subscribe(user_id=22)
    try:
        publish_rfp_ticket_created(
            ticket_id="private-rfp",
            status="analyzing",
            created_at=datetime.now(timezone.utc),
            user_id=23,
        )
        try:
            subscriber_queue.get_nowait()
        except Empty:
            pass
        else:
            raise AssertionError("an event for another user was delivered")
    finally:
        notification_broker.unsubscribe(subscriber_id)


def test_stream_endpoint_returns_sse_headers() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/rfp/tickets/stream", "headers": []})
    response = asyncio.run(stream_rfp_ticket_notifications(request, SimpleNamespace(id=7)))

    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
