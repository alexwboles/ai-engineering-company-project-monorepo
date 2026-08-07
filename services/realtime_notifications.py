"""Small in-process pub/sub broker for HealthCore SSE notifications.

The broker keeps a bounded replay window so a reconnecting dashboard can ask
for events after its last received ID. It intentionally carries only ticket
metadata, never the uploaded document or patient data.
"""

from __future__ import annotations

import itertools
import queue
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Notification:
    event_id: str
    event_name: str
    payload: dict[str, Any]
    audience_user_id: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.event_id,
            "event": self.event_name,
            "data": self.payload,
        }


class NotificationBroker:
    """Thread-safe in-process broker with a bounded replay history."""

    def __init__(self, *, history_size: int = 200) -> None:
        self._history: deque[Notification] = deque(maxlen=history_size)
        self._subscribers: dict[int, tuple[int | None, queue.Queue[Notification]]] = {}
        self._subscriber_ids = itertools.count(1)
        self._event_ids = itertools.count(1)
        self._lock = threading.RLock()

    def publish(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        audience_user_id: int | None = None,
    ) -> Notification:
        with self._lock:
            notification = Notification(
                event_id=str(next(self._event_ids)),
                event_name=event_name,
                payload=dict(payload),
                audience_user_id=audience_user_id,
            )
            self._history.append(notification)
            for subscriber_user_id, subscriber_queue in self._subscribers.values():
                if audience_user_id is None or subscriber_user_id == audience_user_id:
                    subscriber_queue.put_nowait(notification)
            return notification

    def subscribe(
        self,
        *,
        user_id: int | None,
        last_event_id: str | None = None,
    ) -> tuple[int, queue.Queue[Notification]]:
        """Subscribe and enqueue replayable events newer than ``last_event_id``."""

        try:
            last_id = int(last_event_id or "0")
        except ValueError:
            last_id = 0

        subscriber_id = next(self._subscriber_ids)
        subscriber_queue: queue.Queue[Notification] = queue.Queue()
        with self._lock:
            self._subscribers[subscriber_id] = (user_id, subscriber_queue)
            for notification in self._history:
                if int(notification.event_id) <= last_id:
                    continue
                if notification.audience_user_id is None or notification.audience_user_id == user_id:
                    subscriber_queue.put_nowait(notification)
        return subscriber_id, subscriber_queue

    def unsubscribe(self, subscriber_id: int) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def reset_for_tests(self) -> None:
        """Clear broker state without exposing reset functionality to the API."""

        with self._lock:
            self._history.clear()
            self._subscribers.clear()
            self._subscriber_ids = itertools.count(1)
            self._event_ids = itertools.count(1)


notification_broker = NotificationBroker()


def publish_rfp_ticket_created(*, ticket_id: str, status: str, created_at: datetime, user_id: int | None) -> Notification:
    return notification_broker.publish(
        "rfp_ticket_created",
        {
            "ticket_id": ticket_id,
            "status": status,
            "created_at": created_at.isoformat(),
        },
        audience_user_id=user_id,
    )


def publish_rfp_ticket_updated(*, ticket_id: str, status: str, updated_at: datetime, user_id: int | None) -> Notification:
    return notification_broker.publish(
        "rfp_ticket_updated",
        {
            "ticket_id": ticket_id,
            "status": status,
            "updated_at": updated_at.isoformat(),
        },
        audience_user_id=user_id,
    )
