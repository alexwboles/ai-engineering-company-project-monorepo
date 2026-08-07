"""Small in-process pub/sub transport for one API process.

The agent is the producer and WebSocket connections are consumers. A session
has one bounded event log for reconnect replay and one queue per subscriber, so
two clients never cause two calls to the agent.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class SessionEventBus:
    """Fan out immutable events to all subscribers of a chat session."""

    def __init__(self, *, history_limit: int = 200, queue_limit: int = 200) -> None:
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=history_limit)
        )
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._queue_limit = queue_limit
        self._lock = asyncio.Lock()

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        """Record and fan out an event without coupling producers to clients."""

        async with self._lock:
            self._history[session_id].append(event)
            subscribers = tuple(self._subscribers.get(session_id, set()))
            for queue in subscribers:
                if queue.full():
                    # A slow browser must not block the agent or other clients.
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(event)

    async def history(self, session_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._history.get(session_id, ()))

    @asynccontextmanager
    async def subscribe(self, session_id: str) -> AsyncIterator[tuple[asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_limit)
        async with self._lock:
            replay = list(self._history.get(session_id, ()))
            self._subscribers[session_id].add(queue)
        try:
            yield queue, replay
        finally:
            async with self._lock:
                self._subscribers[session_id].discard(queue)
                if not self._subscribers[session_id]:
                    self._subscribers.pop(session_id, None)
