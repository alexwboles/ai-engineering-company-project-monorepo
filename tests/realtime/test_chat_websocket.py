"""Contract tests for the checkpointed WebSocket producer and consumers."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.realtime.session import ChatSessionManager


def test_websocket_route_is_registered() -> None:
    from services.api.main import app

    assert any(getattr(route, "path", None) == "/ws/chat/{session_id}" for route in app.routes)


def test_stream_interrupt_resume_and_pubsub_fanout(monkeypatch) -> None:
    calls: list[str] = []

    def fake_invoke(question: str, *, trace_id: str):
        calls.append(question)
        return {"answer": f"Answer for {question}: one two three four five", "trace_id": trace_id}

    monkeypatch.setattr("services.realtime.session.invoke_agent", fake_invoke)

    async def scenario() -> tuple[list[dict], list[dict]]:
        manager = ChatSessionManager()
        async with manager.subscribe("session-1") as (first, _), manager.subscribe("session-1") as (second, _):
            await manager.connect("session-1")
            await wait_for_event(first, "chat_session_connected")
            await wait_for_event(second, "chat_session_connected")

            await manager.handle_message(
                "session-1",
                {"event_type": "chat_message", "properties": {"message": "first question", "messageId": "m1"}},
            )
            first_events = await collect_until(first, "chat_token_emitted")
            await manager.handle_message(
                "session-1",
                {"event_type": "chat_interrupt", "properties": {"message": "replacement question", "messageId": "m2"}},
            )
            first_events.extend(await collect_until(first, "chat_generation_completed", message_id="m2"))

            second_events = await drain_until_idle(second)
            return first_events, second_events

    first_events, second_events = asyncio.run(scenario())

    assert calls == ["first question", "replacement question"]
    assert any(event["event_type"] == "chat_generation_interrupted" for event in first_events)
    assert any(
        event["event_type"] == "chat_token_emitted" and event["properties"]["messageId"] == "m2"
        for event in first_events
    )
    assert any(
        event["event_type"] == "chat_generation_completed" and event["properties"]["messageId"] == "m2"
        for event in first_events
    )
    assert [event["eventId"] for event in first_events] == [event["eventId"] for event in second_events]
    for event in first_events:
        assert set(event) == {
            "eventId",
            "timestamp",
            "sessionId",
            "userId",
            "event_type",
            "schemaVersion",
            "requestId",
            "properties",
        }


def test_reconnect_replays_the_same_session_history(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.realtime.session.invoke_agent",
        lambda question, *, trace_id: {"answer": "replayed answer", "trace_id": trace_id},
    )

    async def scenario() -> list[dict]:
        manager = ChatSessionManager()
        async with manager.subscribe("session-2") as (queue, _):
            await manager.connect("session-2")
            await wait_for_event(queue, "chat_session_connected")
            await manager.handle_message(
                "session-2",
                {"event_type": "chat_message", "properties": {"message": "status", "messageId": "m1"}},
            )
            await collect_until(queue, "chat_generation_completed", message_id="m1")

        async with manager.subscribe("session-2") as (_queue, replay):
            return replay

    replay = asyncio.run(scenario())
    assert any(event["event_type"] == "chat_token_emitted" for event in replay)
    assert any(event["event_type"] == "chat_generation_completed" for event in replay)


async def wait_for_event(queue, event_type: str, *, timeout: float = 5.0) -> dict:
    while True:
        event = await asyncio.wait_for(queue.get(), timeout)
        if event.get("event_type") == event_type:
            return event


async def collect_until(queue, event_type: str, *, message_id: str | None = None) -> list[dict]:
    collected: list[dict] = []
    while True:
        event = await asyncio.wait_for(queue.get(), 5.0)
        collected.append(event)
        if event.get("event_type") != event_type:
            continue
        if message_id is None or event.get("properties", {}).get("messageId") == message_id:
            return collected


async def drain_until_idle(queue, *, idle_for: float = 0.1) -> list[dict]:
    events: list[dict] = []
    while True:
        try:
            events.append(await asyncio.wait_for(queue.get(), idle_for))
        except asyncio.TimeoutError:
            return events
