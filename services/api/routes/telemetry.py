from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

try:
    from services.api.telemetry_models import TelemetryEvent
    from services.api.telemetry_storage import TelemetryStorageError, event_to_storage_row
except ModuleNotFoundError:
    from telemetry_models import TelemetryEvent
    from telemetry_storage import TelemetryStorageError, event_to_storage_row

logger = logging.getLogger("healthcore.telemetry")

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryBatchEnvelope(BaseModel):
    """Validate only the batch envelope; each event is validated in the handler."""

    model_config = ConfigDict(extra="forbid")

    events: list[Any]


@router.post("/events")
async def receive_telemetry_events(request: Request, payload: TelemetryBatchEnvelope) -> dict[str, int]:
    valid_rows: list[dict[str, Any]] = []
    rejected = 0
    accepted_event_types: list[str] = []

    for raw_event in payload.events:
        try:
            event = TelemetryEvent.model_validate(raw_event)
        except ValidationError as exc:
            rejected += 1
            logger.warning("Rejected telemetry event with %s validation issue(s)", len(exc.errors()))
            continue

        valid_rows.append(event_to_storage_row(event))
        accepted_event_types.append(event.event_type)

    if valid_rows:
        try:
            await request.app.state.telemetry_store.bulk_insert(valid_rows)
        except TelemetryStorageError:
            logger.exception("Telemetry batch persistence failed")
            raise HTTPException(
                status_code=503,
                detail="Telemetry storage is temporarily unavailable. Please retry the batch.",
            ) from None

    logger.info(
        "Processed telemetry batch: received=%s stored=%s rejected=%s event_types=%s",
        len(payload.events),
        len(valid_rows),
        rejected,
        ", ".join(accepted_event_types),
    )
    return {"received": len(payload.events), "stored": len(valid_rows), "rejected": rejected}
