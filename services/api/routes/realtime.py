"""Bidirectional WebSocket transport for the HealthCore support agent."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from services.realtime.session import chat_sessions
except ModuleNotFoundError:  # pragma: no cover - supports running from services/api
    from realtime.session import chat_sessions


router = APIRouter(tags=["realtime"])


@router.websocket("/ws/chat/{session_id}")
async def support_chat_socket(websocket: WebSocket, session_id: str) -> None:
    """Consume client messages and stream one shared producer to all clients."""

    await websocket.accept()
    await chat_sessions.connect(session_id)
    sender: asyncio.Task[None] | None = None

    async with chat_sessions.subscribe(session_id) as (queue, replay):
        async def send_events() -> None:
            for event in replay:
                await websocket.send_json(event)
            while True:
                await websocket.send_json(await queue.get())

        sender = asyncio.create_task(send_events())
        try:
            while True:
                raw = await websocket.receive_json()
                await chat_sessions.handle_message(session_id, raw)
        except WebSocketDisconnect:
            pass
        finally:
            if sender is not None:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
            await chat_sessions.disconnect(session_id)
