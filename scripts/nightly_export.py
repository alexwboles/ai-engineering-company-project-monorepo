"""Export yesterday's telemetry and trigger the business pipeline.

Run from the repository root with the project's Python environment:
    python scripts/nightly_export.py

``TARGET_DATE=YYYY-MM-DD`` is supported for deterministic testing. The CSV is
an audit backup only; the child pipeline continues to read telemetry_events.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import shlex
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from services import job_runner


REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_NAME = job_runner.JOB_NAME
TELEMETRY_COLUMNS = (
    "event_id",
    "timestamp",
    "session_id",
    "user_id",
    "event_type",
    "schema_version",
    "request_id",
    "tags",
)
LOGGER = logging.getLogger("healthcore.nightly_export")


class UtcFormatter(logging.Formatter):
    converter = staticmethod(lambda *_args: datetime.now(timezone.utc).timetuple())


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(UtcFormatter("%(asctime)sZ %(levelname)s %(message)s"))
    LOGGER.setLevel(os.getenv("NIGHTLY_LOG_LEVEL", "INFO").upper())
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.propagate = False


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Load non-secret local configuration without overwriting shell values."""

    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_target_date() -> date:
    override = os.getenv("TARGET_DATE", "").strip()
    if override:
        try:
            return date.fromisoformat(override)
        except ValueError as exc:
            raise ValueError("TARGET_DATE must use YYYY-MM-DD format") from exc
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def telemetry_csv_path(target_date: date) -> Path:
    return REPO_ROOT / "data" / "raw" / f"telemetry_{target_date.isoformat()}.csv"


def export_telemetry_to_csv(target_date: date, output_path: Path) -> int:
    """Write an atomic audit snapshot, returning the number of exported rows."""

    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    query = """
        SELECT event_id, timestamp, session_id, user_id, event_type,
               schema_version, request_id, tags
        FROM public.telemetry_events
        WHERE timestamp >= %s AND timestamp < %s
        ORDER BY timestamp ASC, event_id ASC
    """
    with job_runner.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (start, end))
            rows = cursor.fetchall()
            connection.commit()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TELEMETRY_COLUMNS))
        writer.writeheader()
        for row in rows:
            values = dict(zip(TELEMETRY_COLUMNS, row))
            tags: Any = values.get("tags")
            if isinstance(tags, (dict, list)):
                values["tags"] = json.dumps(tags, separators=(",", ":"), sort_keys=True)
            writer.writerow(values)
    temporary_path.replace(output_path)
    return len(rows)


def pipeline_command() -> list[str]:
    configured = os.getenv("NIGHTLY_PIPELINE_COMMAND", "").strip()
    if configured:
        return shlex.split(configured)
    return [sys.executable, str(REPO_ROOT / "data" / "pipelines" / "pipeline.py")]


def trigger_pipeline() -> None:
    """Run the existing ETL in a separate process, never in the API process."""

    subprocess.run(pipeline_command(), cwd=REPO_ROOT, check=True, env=os.environ.copy())


def log_event(status: str, message: str, *, level: int = logging.INFO) -> None:
    LOGGER.log(level, "job=%s status=%s %s", JOB_NAME, status, message)


def run() -> int:
    configure_logging()
    load_dotenv()
    run_id: str | None = None
    target_date: date | None = None

    try:
        target_date = resolve_target_date()
        if job_runner.has_processing_lock(JOB_NAME):
            log_event("skipped", f"processing lock exists target_date={target_date.isoformat()}")
            return 0
        if job_runner.has_completed_for_date(JOB_NAME, target_date):
            log_event("skipped", f"completed record exists target_date={target_date.isoformat()}")
            return 0

        record = job_runner.create_job_run(JOB_NAME, target_date)
        run_id = str(record["id"])
        if record["status"] == "completed":
            log_event("skipped", f"completed record exists target_date={target_date.isoformat()}")
            return 0
        if record["status"] == "processing" or not job_runner.mark_processing(run_id):
            log_event("skipped", f"processing lock exists target_date={target_date.isoformat()}")
            return 0

        log_event("processing", f"started target_date={target_date.isoformat()}")
        output_path = telemetry_csv_path(target_date)
        if output_path.exists():
            log_event("processing", f"csv_exists path={output_path.name}")
        else:
            exported = export_telemetry_to_csv(target_date, output_path)
            log_event("processing", f"csv_exported rows={exported} path={output_path.name}")

        trigger_pipeline()
        if not job_runner.mark_completed(run_id):
            raise RuntimeError("nightly job could not transition to completed")
        log_event("completed", f"finished target_date={target_date.isoformat()}")
        return 0
    except Exception as exc:
        if run_id is not None:
            try:
                job_runner.mark_failed(run_id, exc)
            except Exception:
                LOGGER.exception("job=%s status=failed status_update_failed", JOB_NAME)
        target_label = target_date.isoformat() if target_date else "unknown"
        log_event("failed", f"target_date={target_label} error={exc}", level=logging.ERROR)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
