from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

try:
    from services.api.telemetry_storage import TelemetryQueryError
    from services.telemetry.analysis import calculate_technical_report
except ModuleNotFoundError:
    from telemetry_storage import TelemetryQueryError
    from services.telemetry.analysis import calculate_technical_report

router = APIRouter(prefix="/telemetry", tags=["telemetry-report"])

REPORT_CACHE_TTL_SECONDS = 60.0
_report_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


@router.get("/report")
async def get_telemetry_report(
    request: Request,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict[str, Any]:
    end = _parse_date(end_date, "end_date") if end_date else datetime.now(timezone.utc)
    start = _parse_date(start_date, "start_date") if start_date else end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=400, detail="start_date must be earlier than end_date.")

    cache_key = (_as_utc_iso(start), _as_utc_iso(end))
    now = time.monotonic()
    async with _cache_lock:
        cached = _report_cache.get(cache_key)
        if cached and now - cached[0] < REPORT_CACHE_TTL_SECONDS:
            return cached[1]

    reader = getattr(request.app.state, "telemetry_reader", request.app.state.telemetry_store)
    try:
        metrics = await calculate_technical_report(reader, start, end)
    except TelemetryQueryError:
        raise HTTPException(
            status_code=503,
            detail="Telemetry reporting is temporarily unavailable. Please try again.",
        ) from None

    report = {
        "period": {"from": _as_utc_iso(start), "to": _as_utc_iso(end)},
        "metrics": metrics,
    }
    async with _cache_lock:
        _report_cache[cache_key] = (time.monotonic(), report)
    return report


def clear_report_cache() -> None:
    _report_cache.clear()


def _parse_date(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid ISO 8601 date or timestamp.",
        ) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
