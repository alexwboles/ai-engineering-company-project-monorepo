from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: str = Field(description="Unique event identifier.")
    timestamp: str = Field(description="ISO 8601 UTC timestamp.")
    sessionId: str = Field(description="Opaque browser or API session identifier.")
    userId: str | None = Field(description="Opaque internal user identifier, or null when anonymous.")
    event_type: str = Field(description="Consistent lower_snake_case entity_action name.")
    schemaVersion: str = Field(description="Version of the event payload schema.")
    requestId: str = Field(description="Correlation ID shared across frontend, backend, and logs.")
    properties: dict[str, Any] = Field(description="Event-specific payload.")


class TelemetryBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent]
