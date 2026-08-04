"""Resilient business-performance pipeline for the HealthCore supply report.

Run from the repository root with:
    uv run --project services/api python data/pipelines/pipeline.py

When the services/api environment is activated, the shorter ``python`` command
from the design document works as well. Supabase is used when its connection
settings are present; otherwise the CLI writes a safe local evaluation result.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from prefect import flow, get_run_logger, task
from prefect.tasks import task_input_hash

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:  # pragma: no cover - the backend dependency installs this.
    psycopg2 = None
    Json = None

LOGGER = logging.getLogger("healthcore.business_pipeline")

REPORTING_NAMESPACE = "reporting.business_metrics"
REPORTING_TABLE = "monthly_clinic_supply_performance"
PIPELINE_RUNS_TABLE = "pipeline_runs"
EVENT_FACTS_TABLE = "monthly_supply_event_facts"
SOURCE_TABLE = "telemetry_events"
SOURCE_EVENT_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_threshold_triggered",
    "supply_expiry_flagged",
)

# Three attempts absorb short Supabase/network interruptions without keeping a
# broken scheduled run alive indefinitely. The load is still idempotent.
EXTERNAL_RETRIES = 3
EXTERNAL_RETRY_DELAY_SECONDS = 10


@dataclass(frozen=True)
class PipelineSettings:
    repo_root: Path
    source_file: Path
    local_metrics_file: Path
    local_runs_file: Path
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    telemetry_table: str
    request_timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls) -> "PipelineSettings":
        root = Path(__file__).resolve().parents[2]
        source_file = Path(
            os.getenv("DATA_PIPELINE_SOURCE_FILE", str(root / "data" / "raw" / "telemetry_events.json"))
        )
        if not source_file.is_absolute():
            source_file = root / source_file

        return cls(
            repo_root=root,
            source_file=source_file,
            local_metrics_file=root / "data" / "eval" / "business_metrics.json",
            local_runs_file=root / "data" / "eval" / "pipeline_runs.json",
            database_url=os.getenv("DATABASE_URL", "").strip(),
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            telemetry_table=os.getenv("SUPABASE_TELEMETRY_TABLE", SOURCE_TABLE).strip() or SOURCE_TABLE,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_start(value: str | date | None) -> date:
    if value is None:
        today = _utc_now().date()
        current_month = today.replace(day=1)
        return (current_month - timedelta(days=1)).replace(day=1)
    if isinstance(value, date):
        parsed = value
    else:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("month_start must be an ISO 8601 date in YYYY-MM-DD format") from exc
    if parsed.day != 1:
        raise ValueError("month_start must be the first day of a calendar month")
    return parsed


def _month_end(month: date) -> date:
    return (month.replace(day=28) + timedelta(days=4)).replace(day=1)


def _iso(value: datetime | date) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value.isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _positive_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _required_text(properties: dict[str, Any], key: str) -> str | None:
    value = properties.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _safe_error_code(error: BaseException) -> str:
    return type(error).__name__.upper()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read local pipeline file: {path.name}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _using_postgres(settings: PipelineSettings) -> bool:
    return bool(settings.database_url)


def _using_supabase_rest(settings: PipelineSettings) -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _connect(settings: PipelineSettings):
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for DATABASE_URL pipeline execution")
    return psycopg2.connect(settings.database_url, connect_timeout=int(settings.request_timeout_seconds))


def _ensure_reporting_schema(cursor: Any) -> None:
    cursor.execute("CREATE SCHEMA IF NOT EXISTS reporting")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS reporting.{REPORTING_TABLE} (
            id uuid PRIMARY KEY,
            clinic_id text NOT NULL,
            country text NOT NULL CHECK (country IN ('US', 'UK')),
            month_start date NOT NULL,
            total_supply_cost numeric NOT NULL DEFAULT 0,
            supply_consumption_count integer NOT NULL DEFAULT 0,
            critical_stockout_count integer NOT NULL DEFAULT 0,
            expiry_risk_count integer NOT NULL DEFAULT 0,
            currency text NOT NULL CHECK (currency IN ('USD', 'GBP')),
            computed_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (clinic_id, month_start)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
            run_id uuid PRIMARY KEY,
            flow_name text NOT NULL,
            trigger_type text NOT NULL,
            requested_month_start date NOT NULL,
            started_at timestamptz NOT NULL,
            ended_at timestamptz,
            status text NOT NULL,
            checkpoint text NOT NULL,
            records_extracted integer NOT NULL DEFAULT 0,
            records_processed integer NOT NULL DEFAULT 0,
            records_published integer NOT NULL DEFAULT 0,
            records_rejected integer NOT NULL DEFAULT 0,
            source_max_timestamp timestamptz,
            error_code text,
            error_message text
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reporting.monthly_supply_event_facts (
            run_id uuid NOT NULL,
            event_id text NOT NULL,
            event_type text NOT NULL,
            clinic_id text NOT NULL,
            country text NOT NULL,
            department text,
            month_start date NOT NULL,
            event_timestamp timestamptz NOT NULL,
            normalized_total_cost numeric NOT NULL DEFAULT 0,
            included boolean NOT NULL,
            rejection_reason text,
            PRIMARY KEY (run_id, event_id)
        )
        """
    )


def _upsert_run_record(settings: PipelineSettings, record: dict[str, Any]) -> None:
    if _using_postgres(settings):
        with _connect(settings) as connection:
            with connection.cursor() as cursor:
                _ensure_reporting_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO reporting.pipeline_runs (
                        run_id, flow_name, trigger_type, requested_month_start,
                        started_at, ended_at, status, checkpoint,
                        records_extracted, records_processed, records_published,
                        records_rejected, source_max_timestamp, error_code, error_message
                    ) VALUES (
                        %(run_id)s, %(flow_name)s, %(trigger_type)s, %(requested_month_start)s,
                        %(started_at)s, %(ended_at)s, %(status)s, %(checkpoint)s,
                        %(records_extracted)s, %(records_processed)s, %(records_published)s,
                        %(records_rejected)s, %(source_max_timestamp)s, %(error_code)s, %(error_message)s
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        ended_at = EXCLUDED.ended_at,
                        status = EXCLUDED.status,
                        checkpoint = EXCLUDED.checkpoint,
                        records_extracted = EXCLUDED.records_extracted,
                        records_processed = EXCLUDED.records_processed,
                        records_published = EXCLUDED.records_published,
                        records_rejected = EXCLUDED.records_rejected,
                        source_max_timestamp = EXCLUDED.source_max_timestamp,
                        error_code = EXCLUDED.error_code,
                        error_message = EXCLUDED.error_message
                    """,
                    record,
                )
            connection.commit()
        return

    rows = _read_json(settings.local_runs_file, [])
    if not isinstance(rows, list):
        rows = []
    updated = False
    for index, existing in enumerate(rows):
        if isinstance(existing, dict) and existing.get("run_id") == record["run_id"]:
            rows[index] = record
            updated = True
            break
    if not updated:
        rows.append(record)
    _write_json(settings.local_runs_file, rows)


@task(
    name="start_pipeline_run",
    retries=EXTERNAL_RETRIES,
    retry_delay_seconds=EXTERNAL_RETRY_DELAY_SECONDS,
)
def start_pipeline_run(
    settings: PipelineSettings,
    run_id: str,
    flow_name: str,
    trigger_type: str,
    month_start: str,
) -> dict[str, Any]:
    started_at = _utc_now()
    record = {
        "run_id": run_id,
        "flow_name": flow_name,
        "trigger_type": trigger_type,
        "requested_month_start": month_start,
        "started_at": _iso(started_at),
        "ended_at": None,
        "status": "RUNNING",
        "checkpoint": "STARTED",
        "records_extracted": 0,
        "records_processed": 0,
        "records_published": 0,
        "records_rejected": 0,
        "source_max_timestamp": None,
        "error_code": None,
        "error_message": None,
    }
    _upsert_run_record(settings, record)
    return record


def _fetch_postgres_events(settings: PipelineSettings, month: date) -> list[dict[str, Any]]:
    start = datetime.combine(month, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(_month_end(month), datetime.min.time(), tzinfo=timezone.utc)
    query = f"""
        SELECT event_id, timestamp, event_type, schema_version, request_id, tags
        FROM public.{settings.telemetry_table}
        WHERE event_type = ANY(%s)
          AND timestamp >= %s
          AND timestamp < %s
        ORDER BY timestamp ASC, event_id ASC
    """
    with _connect(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (list(SOURCE_EVENT_TYPES), start, end))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_supabase_events(settings: PipelineSettings, month: date) -> list[dict[str, Any]]:
    start = datetime.combine(month, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(_month_end(month), datetime.min.time(), tzinfo=timezone.utc)
    endpoint = f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.telemetry_table}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Accept": "application/json",
    }
    params = [
        ("select", "event_id,timestamp,event_type,schema_version,request_id,tags"),
        ("event_type", f"in.({','.join(SOURCE_EVENT_TYPES)})"),
        ("timestamp", f"gte.{_iso(start)}"),
        ("timestamp", f"lt.{_iso(end)}"),
        ("order", "timestamp.asc,event_id.asc"),
    ]
    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Telemetry REST extraction failed") from exc
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise RuntimeError("Telemetry REST extraction returned an unexpected shape")
    return payload


@task(
    name="extract_monthly_supply_events",
    retries=EXTERNAL_RETRIES,
    retry_delay_seconds=EXTERNAL_RETRY_DELAY_SECONDS,
)
def extract_monthly_supply_events(settings: PipelineSettings, month_start: str) -> list[dict[str, Any]]:
    month = _month_start(month_start)
    if _using_postgres(settings):
        return _fetch_postgres_events(settings, month)
    if _using_supabase_rest(settings):
        return _fetch_supabase_events(settings, month)

    if settings.source_file.exists():
        payload = _read_json(settings.source_file, [])
        if not isinstance(payload, list):
            raise RuntimeError("Local telemetry source must contain a JSON array")
        return payload

    get_run_logger().warning(
        "No telemetry database or local source file configured; running an empty local evaluation window"
    )
    return []


def _source_max_timestamp(rows: list[dict[str, Any]]) -> str | None:
    timestamps = [
        parsed
        for row in rows
        if isinstance(row, dict)
        for parsed in [_parse_timestamp(row.get("timestamp"))]
        if parsed is not None
    ]
    return _iso(max(timestamps)) if timestamps else None


def _event_properties(row: dict[str, Any]) -> dict[str, Any]:
    properties = row.get("tags", row.get("properties", {}))
    return properties if isinstance(properties, dict) else {}


def _normalize_fact(row: dict[str, Any], month: date) -> tuple[dict[str, Any] | None, str | None]:
    event_id = row.get("event_id", row.get("eventId"))
    event_type = row.get("event_type")
    timestamp = _parse_timestamp(row.get("timestamp"))
    properties = _event_properties(row)
    if not isinstance(event_id, str) or not event_id.strip():
        return None, "MISSING_EVENT_ID"
    if event_type not in SOURCE_EVENT_TYPES:
        return None, "UNSUPPORTED_EVENT_TYPE"
    if timestamp is None or timestamp.date() < month or timestamp.date() >= _month_end(month):
        return None, "EVENT_OUTSIDE_REQUESTED_MONTH"

    clinic_id = _required_text(properties, "clinic_id")
    country = _required_text(properties, "country")
    if clinic_id is None:
        return None, "MISSING_CLINIC_ID"
    if country not in {"US", "UK"}:
        return None, "INVALID_COUNTRY"

    quantity = _positive_decimal(properties.get("quantity", 1))
    if quantity is None or quantity <= 0:
        return None, "INVALID_QUANTITY"

    total_cost = Decimal("0")
    if event_type == "inbound_order_created":
        direct_cost = _positive_decimal(properties.get("total_cost"))
        unit_cost = _positive_decimal(properties.get("unit_cost"))
        if direct_cost is not None:
            total_cost = direct_cost
        elif unit_cost is not None:
            total_cost = unit_cost * quantity
        else:
            return None, "MISSING_SUPPLY_COST"

    currency = "USD" if country == "US" else "GBP"
    supplied_currency = properties.get("currency")
    if supplied_currency is not None and supplied_currency != currency:
        return None, "CURRENCY_COUNTRY_MISMATCH"

    return {
        "event_id": event_id.strip(),
        "event_type": event_type,
        "event_timestamp": _iso(timestamp),
        "request_id": row.get("request_id", row.get("requestId")),
        "clinic_id": clinic_id,
        "country": country,
        "department": _required_text(properties, "department"),
        "month_start": month.isoformat(),
        "currency": currency,
        "normalized_total_cost": float(total_cost.quantize(Decimal("0.01"))),
    }, None


@task(
    name="validate_and_deduplicate_supply_events",
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
def validate_and_deduplicate_supply_events(
    raw_rows: list[dict[str, Any]], month_start: str
) -> dict[str, Any]:
    """Normalize the source snapshot; the cache is valid for one hour.

    The cache key includes both the raw rows and target month through
    ``task_input_hash``. A new source snapshot or a different month therefore
    cannot reuse an unrelated transformation result.
    """

    month = _month_start(month_start)
    facts_by_event_id: dict[str, dict[str, Any]] = {}
    rejected = 0
    rejection_codes: dict[str, int] = {}

    for row in raw_rows:
        if not isinstance(row, dict):
            rejected += 1
            rejection_codes["INVALID_SOURCE_ROW"] = rejection_codes.get("INVALID_SOURCE_ROW", 0) + 1
            continue
        fact, rejection = _normalize_fact(row, month)
        if fact is None:
            rejected += 1
            code = rejection or "INVALID_EVENT"
            rejection_codes[code] = rejection_codes.get(code, 0) + 1
            continue
        existing = facts_by_event_id.get(fact["event_id"])
        if existing is None:
            facts_by_event_id[fact["event_id"]] = fact
        elif existing != fact:
            rejected += 1
            rejection_codes["SOURCE_EVENT_CONFLICT"] = rejection_codes.get("SOURCE_EVENT_CONFLICT", 0) + 1

    return {
        "facts": list(facts_by_event_id.values()),
        "records_extracted": len(raw_rows),
        "records_processed": len(facts_by_event_id),
        "records_rejected": rejected,
        "rejection_codes": rejection_codes,
    }


@task(
    name="aggregate_monthly_clinic_supply_metrics",
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
def aggregate_monthly_clinic_supply_metrics(
    validation_result: dict[str, Any], month_start: str
) -> dict[str, Any]:
    """Calculate one deterministic board row per clinic and UTC month."""

    month = _month_start(month_start)
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    department_counts: dict[tuple[str, str], int] = {}
    for fact in validation_result.get("facts", []):
        key = (fact["clinic_id"], fact["country"], month.isoformat())
        row = grouped.setdefault(
            key,
            {
                "clinic_id": fact["clinic_id"],
                "country": fact["country"],
                "month_start": month.isoformat(),
                "total_supply_cost": Decimal("0"),
                "supply_consumption_count": 0,
                "critical_stockout_count": 0,
                "expiry_risk_count": 0,
                "currency": fact["currency"],
            },
        )
        event_type = fact["event_type"]
        if event_type == "inbound_order_created":
            row["total_supply_cost"] += Decimal(str(fact["normalized_total_cost"]))
        elif event_type == "outbound_order_created":
            row["supply_consumption_count"] += 1
            department = fact.get("department") or "unassigned"
            department_key = (fact["clinic_id"], department)
            department_counts[department_key] = department_counts.get(department_key, 0) + 1
        elif event_type == "stock_threshold_triggered":
            row["critical_stockout_count"] += 1
        elif event_type == "supply_expiry_flagged":
            row["expiry_risk_count"] += 1

    rows = []
    for row in grouped.values():
        row["total_supply_cost"] = float(row["total_supply_cost"].quantize(Decimal("0.01")))
        rows.append(row)
    rows.sort(key=lambda item: (item["clinic_id"], item["country"], item["month_start"]))
    return {
        "rows": rows,
        "department_counts": [
            {"clinic_id": clinic_id, "department": department, "count": count}
            for (clinic_id, department), count in sorted(department_counts.items())
        ],
    }


def _publish_to_database(
    settings: PipelineSettings,
    run_id: str,
    facts: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
) -> int:
    with _connect(settings) as connection:
        with connection.cursor() as cursor:
            _ensure_reporting_schema(cursor)
            if Json is None:
                raise RuntimeError("psycopg2 JSON support is unavailable")
            for fact in facts:
                cursor.execute(
                    f"""
                    INSERT INTO reporting.{EVENT_FACTS_TABLE} (
                        run_id, event_id, event_type, clinic_id, country, department,
                        month_start, event_timestamp, normalized_total_cost, included,
                        rejection_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NULL)
                    ON CONFLICT (run_id, event_id) DO NOTHING
                    """,
                    (
                        run_id,
                        fact["event_id"],
                        fact["event_type"],
                        fact["clinic_id"],
                        fact["country"],
                        fact.get("department"),
                        fact["month_start"],
                        fact["event_timestamp"],
                        fact["normalized_total_cost"],
                    ),
                )
            for row in aggregate_rows:
                cursor.execute(
                    f"""
                    INSERT INTO reporting.{REPORTING_TABLE} (
                        id, clinic_id, country, month_start, total_supply_cost,
                        supply_consumption_count, critical_stockout_count,
                        expiry_risk_count, currency, computed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (clinic_id, month_start) DO UPDATE SET
                        country = EXCLUDED.country,
                        total_supply_cost = EXCLUDED.total_supply_cost,
                        supply_consumption_count = EXCLUDED.supply_consumption_count,
                        critical_stockout_count = EXCLUDED.critical_stockout_count,
                        expiry_risk_count = EXCLUDED.expiry_risk_count,
                        currency = EXCLUDED.currency,
                        computed_at = EXCLUDED.computed_at
                    """,
                    (
                        str(uuid.uuid4()),
                        row["clinic_id"],
                        row["country"],
                        row["month_start"],
                        row["total_supply_cost"],
                        row["supply_consumption_count"],
                        row["critical_stockout_count"],
                        row["expiry_risk_count"],
                        row["currency"],
                    ),
                )
            connection.commit()
    return len(aggregate_rows)


def _publish_to_local_file(settings: PipelineSettings, aggregate_rows: list[dict[str, Any]]) -> int:
    payload = {
        "schema": REPORTING_NAMESPACE.split(".", maxsplit=1)[0],
        "table": REPORTING_TABLE,
        "rows": aggregate_rows,
        "computed_at": _iso(_utc_now()),
    }
    _write_json(settings.local_metrics_file, payload)
    return len(aggregate_rows)


@task(
    name="publish_monthly_clinic_supply_performance",
    retries=EXTERNAL_RETRIES,
    retry_delay_seconds=EXTERNAL_RETRY_DELAY_SECONDS,
)
def publish_monthly_clinic_supply_performance(
    settings: PipelineSettings,
    run_id: str,
    validation_result: dict[str, Any],
    aggregate_result: dict[str, Any],
) -> dict[str, int]:
    facts = validation_result.get("facts", [])
    rows = aggregate_result.get("rows", [])
    if _using_postgres(settings):
        published = _publish_to_database(settings, run_id, facts, rows)
    else:
        published = _publish_to_local_file(settings, rows)
    return {"records_published": published}


@task(
    name="complete_pipeline_run",
    retries=EXTERNAL_RETRIES,
    retry_delay_seconds=EXTERNAL_RETRY_DELAY_SECONDS,
)
def complete_pipeline_run(
    settings: PipelineSettings,
    run_record: dict[str, Any],
    *,
    status: str,
    checkpoint: str,
    records_extracted: int,
    records_processed: int,
    records_published: int,
    records_rejected: int,
    source_max_timestamp: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    completed = dict(run_record)
    completed.update(
        {
            "ended_at": _iso(_utc_now()),
            "status": status,
            "checkpoint": checkpoint,
            "records_extracted": records_extracted,
            "records_processed": records_processed,
            "records_published": records_published,
            "records_rejected": records_rejected,
            "source_max_timestamp": source_max_timestamp,
            "error_code": error_code,
            "error_message": f"Pipeline stopped during {checkpoint.lower()}." if error_code else None,
        }
    )
    _upsert_run_record(settings, completed)
    return completed


@task(
    name="record_pipeline_checkpoint",
    retries=EXTERNAL_RETRIES,
    retry_delay_seconds=EXTERNAL_RETRY_DELAY_SECONDS,
)
def record_pipeline_checkpoint(
    settings: PipelineSettings,
    run_record: dict[str, Any],
    *,
    checkpoint: str,
    records_extracted: int,
    records_processed: int,
    records_published: int,
    records_rejected: int,
    source_max_timestamp: str | None,
) -> dict[str, Any]:
    """Persist the last durable stage so a later run can recover safely."""

    checkpointed = dict(run_record)
    checkpointed.update(
        {
            "status": "RUNNING",
            "checkpoint": checkpoint,
            "records_extracted": records_extracted,
            "records_processed": records_processed,
            "records_published": records_published,
            "records_rejected": records_rejected,
            "source_max_timestamp": source_max_timestamp,
        }
    )
    _upsert_run_record(settings, checkpointed)
    return checkpointed


@task(retries=1, retry_delay_seconds=5)
def publish_run_notification(summary: dict[str, Any]) -> dict[str, str]:
    """Optional notification; its failure must not fail the business flow."""

    logger = get_run_logger()
    notification_url = os.getenv("PIPELINE_NOTIFICATION_URL", "").strip()
    if not notification_url:
        logger.info("No PIPELINE_NOTIFICATION_URL configured; notification skipped")
        return {"status": "skipped"}
    try:
        response = httpx.post(notification_url, json=summary, timeout=5.0)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Pipeline notification failed") from exc
    return {"status": "sent"}


def _run_pipeline(month_start: str | None, trigger_type: str) -> dict[str, Any]:
    settings = PipelineSettings.from_environment()
    target_month = _month_start(month_start).isoformat()
    flow_name = "monthly_clinic_supply_performance_flow"
    run_id = str(uuid.uuid4())
    run_record = start_pipeline_run(settings, run_id, flow_name, trigger_type, target_month)
    raw_rows: list[dict[str, Any]] = []
    source_max_timestamp: str | None = None
    validation_result: dict[str, Any] = {"records_rejected": 0, "records_processed": 0, "facts": []}
    aggregate_result: dict[str, Any] = {"rows": []}
    published = 0

    try:
        raw_rows = extract_monthly_supply_events(settings, target_month)
        source_max_timestamp = _source_max_timestamp(raw_rows)
        run_record = record_pipeline_checkpoint(
            settings,
            run_record,
            checkpoint="EXTRACTED",
            records_extracted=len(raw_rows),
            records_processed=0,
            records_published=0,
            records_rejected=0,
            source_max_timestamp=source_max_timestamp,
        )
        validation_result = validate_and_deduplicate_supply_events(raw_rows, target_month)
        aggregate_result = aggregate_monthly_clinic_supply_metrics(validation_result, target_month)
        run_record = record_pipeline_checkpoint(
            settings,
            run_record,
            checkpoint="TRANSFORMED",
            records_extracted=len(raw_rows),
            records_processed=validation_result.get("records_processed", 0),
            records_published=0,
            records_rejected=validation_result.get("records_rejected", 0),
            source_max_timestamp=source_max_timestamp,
        )
        publish_result = publish_monthly_clinic_supply_performance(
            settings,
            run_id,
            validation_result,
            aggregate_result,
        )
        published = publish_result["records_published"]
        run_record = record_pipeline_checkpoint(
            settings,
            run_record,
            checkpoint="PUBLISHED",
            records_extracted=len(raw_rows),
            records_processed=validation_result.get("records_processed", 0),
            records_published=published,
            records_rejected=validation_result.get("records_rejected", 0),
            source_max_timestamp=source_max_timestamp,
        )
        completed = complete_pipeline_run(
            settings,
            run_record,
            status="COMPLETED",
            checkpoint="COMPLETED",
            records_extracted=len(raw_rows),
            records_processed=validation_result.get("records_processed", 0),
            records_published=published,
            records_rejected=validation_result.get("records_rejected", 0),
            source_max_timestamp=source_max_timestamp,
        )
    except Exception as exc:
        LOGGER.exception("Business pipeline failed at run %s", run_id)
        completed = complete_pipeline_run(
            settings,
            run_record,
            status="FAILED",
            checkpoint="FAILED",
            records_extracted=len(raw_rows),
            records_processed=validation_result.get("records_processed", 0),
            records_published=published,
            records_rejected=validation_result.get("records_rejected", 0),
            source_max_timestamp=source_max_timestamp,
            error_code=_safe_error_code(exc),
        )
        try:
            publish_run_notification(completed, return_state=True)
        except Exception:
            LOGGER.warning("Optional failure notification could not be submitted")
        raise

    # Optional notification is deliberately state-returning so a failed alert
    # cannot interrupt a successfully published business report.
    notification_state = publish_run_notification(completed, return_state=True)
    if hasattr(notification_state, "is_failed") and notification_state.is_failed():
        LOGGER.warning("Optional pipeline notification failed; report remains completed")
    return completed


@flow(name="monthly_clinic_supply_performance_flow", log_prints=True)
def monthly_clinic_supply_performance_flow(month_start: str | None = None) -> dict[str, Any]:
    """Run the scheduled previous-month business report."""

    return _run_pipeline(month_start, "scheduled")


@flow(name="monthly_clinic_supply_backfill_flow", log_prints=True)
def monthly_clinic_supply_backfill_flow(month_start: str | None = None) -> dict[str, Any]:
    """Run a requested month for a manual correction or backfill."""

    return _run_pipeline(month_start, "manual")


def read_monthly_report(month_start: str | None = None) -> dict[str, Any]:
    """Read the business report without embedding query logic in FastAPI."""

    settings = PipelineSettings.from_environment()
    requested_month = _month_start(month_start).isoformat() if month_start else None
    if _using_postgres(settings):
        with _connect(settings) as connection:
            with connection.cursor() as cursor:
                target = requested_month
                if target is None:
                    cursor.execute(f"SELECT max(month_start) FROM reporting.{REPORTING_TABLE}")
                    result = cursor.fetchone()
                    target = result[0].isoformat() if result and result[0] else None
                if target is None:
                    return {"month_start": None, "clinics": []}
                cursor.execute(
                    f"""
                    SELECT clinic_id, country, month_start, total_supply_cost,
                           supply_consumption_count, critical_stockout_count,
                           expiry_risk_count, currency
                    FROM reporting.{REPORTING_TABLE}
                    WHERE month_start = %s
                    ORDER BY clinic_id
                    """,
                    (target,),
                )
                columns = [description[0] for description in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                for row in rows:
                    row["month_start"] = row["month_start"].isoformat()
                return {"month_start": target, "clinics": rows}

    payload = _read_json(settings.local_metrics_file, {})
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if requested_month:
        rows = [row for row in rows if row.get("month_start") == requested_month]
    latest = requested_month or (rows[0].get("month_start") if rows else None)
    return {"month_start": latest, "clinics": rows}


def get_latest_pipeline_run() -> dict[str, Any] | None:
    """Read the latest execution metadata for the reporting status endpoint."""

    settings = PipelineSettings.from_environment()
    if _using_postgres(settings):
        with _connect(settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT run_id, flow_name, trigger_type, requested_month_start,
                           started_at, ended_at, status, checkpoint,
                           records_extracted, records_processed, records_published,
                           records_rejected, source_max_timestamp, error_code, error_message
                    FROM reporting.pipeline_runs
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                columns = [description[0] for description in cursor.description]
                result = dict(zip(columns, row))
                for key, value in result.items():
                    if isinstance(value, (datetime, date)):
                        result[key] = _iso(value)
                return result

    rows = _read_json(settings.local_runs_file, [])
    if not isinstance(rows, list) or not rows:
        return None
    records = [row for row in rows if isinstance(row, dict)]
    return max(records, key=lambda row: str(row.get("started_at", "")), default=None)


def _parse_cli_args() -> str | None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the HealthCore business performance pipeline")
    parser.add_argument("--month-start", help="UTC calendar month start, for example 2026-07-01")
    return parser.parse_args().month_start


if __name__ == "__main__":
    result = monthly_clinic_supply_performance_flow(month_start=_parse_cli_args())
    print(json.dumps(result, indent=2, sort_keys=True))
