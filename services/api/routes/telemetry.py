from __future__ import annotations

import logging

from fastapi import APIRouter

try:
    from services.api.telemetry_models import TelemetryBatchRequest
except ModuleNotFoundError:
    from telemetry_models import TelemetryBatchRequest

logger = logging.getLogger("healthcore.telemetry")

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events")
def receive_telemetry_events(payload: TelemetryBatchRequest) -> dict[str, int]:
    event_types = ", ".join(event.event_type for event in payload.events)
    logger.info("Received telemetry batch with %s events: %s", len(payload.events), event_types)
    return {"received": len(payload.events)}
