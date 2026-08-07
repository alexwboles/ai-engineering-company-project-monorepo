"""Structured event contracts shared by the producer and WebSocket clients.

The fields intentionally mirror the telemetry envelope used by the backoffice:
``eventId``, ``timestamp``, ``sessionId``, ``userId``, ``event_type``,
``schemaVersion``, ``requestId``, and ``properties``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

CHAT_SESSION_CONNECTED = "chat_session_connected"
CHAT_MESSAGE_RECEIVED = "chat_message_received"
CHAT_GENERATION_STARTED = "chat_generation_started"
CHAT_TOKEN_EMITTED = "chat_token_emitted"
CHAT_GENERATION_INTERRUPTED = "chat_generation_interrupted"
CHAT_GENERATION_COMPLETED = "chat_generation_completed"
CHAT_GENERATION_FAILED = "chat_generation_failed"
CHAT_PROTOCOL_ERROR = "chat_protocol_error"

SCHEMA_VERSION = "1.0.0"


def build_event(
    session_id: str,
    event_type: str,
    properties: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create one safe, serialisable event using the existing envelope shape."""

    return {
        "eventId": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sessionId": session_id,
        "userId": user_id,
        "event_type": event_type,
        "schemaVersion": SCHEMA_VERSION,
        "requestId": request_id or str(uuid4()),
        "properties": properties or {},
    }
