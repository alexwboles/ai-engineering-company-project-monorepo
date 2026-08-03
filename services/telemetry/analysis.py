from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Protocol

import pandas as pd


class TelemetryReader(Protocol):
    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Load the bounded event set required by a metric."""


ERROR_EVENT_TYPES = (
    "auth_login_failed",
    "backend_unhandled_exception",
    "claim_validation_failed",
    "frontend_error_occurred",
)
AUTH_EVENT_TYPES = ("auth_login_attempted", "auth_login_failed")


async def events_per_day(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    rows = await reader.fetch_events(start_date, end_date)
    frame = _prepare_frame(rows)
    if frame.empty:
        return []

    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    result = (
        frame.groupby("date", as_index=False)
        .agg(event_count=("event_type", "size"))
        .sort_values("date")
    )
    return result.to_dict(orient="records")


async def event_volume_by_type(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    rows = await reader.fetch_events(start_date, end_date)
    frame = _prepare_frame(rows)
    if frame.empty:
        return []

    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    result = (
        frame.groupby(["date", "event_type"], as_index=False)
        .agg(event_count=("event_type", "size"))
        .sort_values(["date", "event_count", "event_type"], ascending=[True, False, True])
    )
    return result.to_dict(orient="records")


async def error_rate_by_type(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    # The date-bounded SQL load includes the denominator and all approved error types.
    rows = await reader.fetch_events(start_date, end_date)
    frame = _prepare_frame(rows)
    if frame.empty:
        return []

    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame["is_error"] = frame["event_type"].isin(ERROR_EVENT_TYPES)
    totals = frame.groupby("date", as_index=False).agg(total_events=("event_type", "size"))
    errors = frame[frame["is_error"]]
    if errors.empty:
        return []

    result = (
        errors.groupby(["date", "event_type"], as_index=False)
        .agg(error_count=("event_type", "size"))
        .merge(totals, on="date", how="left")
    )
    result["error_rate_percent"] = (result["error_count"] / result["total_events"] * 100).round(2)
    return result.sort_values(["date", "error_rate_percent", "event_type"], ascending=[True, False, True]).to_dict(
        orient="records"
    )


async def latency_by_route(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    rows = await reader.fetch_events(start_date, end_date, ("api_latency_recorded",))
    frame = _prepare_frame(rows)
    if frame.empty:
        return []

    frame["route"] = frame["tags"].map(lambda tags: tags.get("route"))
    frame["duration_ms"] = frame["tags"].map(lambda tags: tags.get("durationMs"))
    frame["duration_ms"] = pd.to_numeric(frame["duration_ms"], errors="coerce")
    frame = frame.dropna(subset=["route", "duration_ms"])
    if frame.empty:
        return []

    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    result = (
        frame.groupby(["date", "route"], as_index=False)
        .agg(
            request_count=("route", "size"),
            average_duration_ms=("duration_ms", "mean"),
            maximum_duration_ms=("duration_ms", "max"),
        )
        .sort_values(["date", "average_duration_ms", "route"], ascending=[True, False, True])
    )
    result["average_duration_ms"] = result["average_duration_ms"].round(2)
    result["maximum_duration_ms"] = result["maximum_duration_ms"].round(2)
    return result.to_dict(orient="records")


async def auth_failure_rate(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    rows = await reader.fetch_events(start_date, end_date, AUTH_EVENT_TYPES)
    frame = _prepare_frame(rows)
    if frame.empty:
        return []

    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame["failed_attempt"] = (frame["event_type"] == "auth_login_failed").astype(int)
    result = (
        frame.groupby("date", as_index=False)
        .agg(
            total_login_attempts=("event_type", "size"),
            failed_login_attempts=("failed_attempt", "sum"),
        )
        .sort_values("date")
    )
    result["failure_rate_percent"] = (
        result["failed_login_attempts"] / result["total_login_attempts"] * 100
    ).round(2)
    return result.to_dict(orient="records")


async def calculate_technical_report(
    reader: TelemetryReader,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, list[dict[str, Any]]]:
    events, volume, errors, latency, auth = await asyncio.gather(
        events_per_day(reader, start_date, end_date),
        event_volume_by_type(reader, start_date, end_date),
        error_rate_by_type(reader, start_date, end_date),
        latency_by_route(reader, start_date, end_date),
        auth_failure_rate(reader, start_date, end_date),
    )
    return {
        "events_per_day": events,
        "event_volume_by_type": volume,
        "error_rate_by_type": errors,
        "latency_by_route": latency,
        "auth_failure_rate": auth,
    }


def _prepare_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "event_type", "tags"])

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).copy()
    frame["event_type"] = frame["event_type"].fillna("").astype(str)
    frame["tags"] = frame["tags"].map(lambda tags: tags if isinstance(tags, dict) else {})
    return frame
