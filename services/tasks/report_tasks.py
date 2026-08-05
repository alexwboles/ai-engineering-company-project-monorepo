"""Background tasks for long-running incident CSV analysis."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict
from pathlib import Path

from services.api.incident_analysis import load_and_analyze_csv, now_iso, summary_to_csv_text, summary_to_dict
from services.celery_app import celery_app
from services.dlq import record_dlq_entry


logger = logging.getLogger("healthcore.tasks")
RESULTS_DIR_NAME = "results"


def _write_latest_result(input_path: Path, payload: dict[str, object], summary_csv: str) -> None:
    results_dir = input_path.parent / RESULTS_DIR_NAME
    results_dir.mkdir(parents=True, exist_ok=True)

    result_json = results_dir / "latest_results.json"
    result_csv = results_dir / "latest_results.csv"
    temporary_json = result_json.with_suffix(".json.tmp")
    temporary_csv = result_csv.with_suffix(".csv.tmp")
    temporary_json.write_text(json.dumps(payload), encoding="utf-8")
    temporary_csv.write_text(summary_csv, encoding="utf-8")
    os.replace(temporary_json, result_json)
    os.replace(temporary_csv, result_csv)


def _remove_upload(input_path: Path) -> None:
    try:
        input_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Unable to remove completed task input path=%s", input_path)


@celery_app.task(
    bind=True,
    name="healthcore.analyze_incident_csv",
    acks_late=True,
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=240,
    time_limit=300,
)
def analyze_incident_csv(self, csv_path: str) -> dict[str, object]:
    """Analyze a CSV referenced by path and return a JSON-safe summary.

    The task receives a path instead of file contents so the Redis message
    remains small. Retries use 10, 20, and 40 second countdowns, absorbing
    transient failures without hammering the analysis worker.
    """

    started = time.monotonic()
    task_id = self.request.id or "local-task"
    attempt = self.request.retries + 1
    input_path = Path(csv_path)

    try:
        summary, invalid_records, _valid_rows = load_and_analyze_csv(input_path)
        payload: dict[str, object] = {
            "generated_at": now_iso(),
            "summary": summary_to_dict(summary),
            "invalid_records": [asdict(issue) for issue in invalid_records],
        }
        _write_latest_result(input_path, payload, summary_to_csv_text(summary))
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "task_id=%s attempt=%s status=success duration_ms=%s",
            task_id,
            attempt,
            duration_ms,
        )
        _remove_upload(input_path)
        return payload
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.error(
            "task_id=%s attempt=%s status=failure duration_ms=%s error=%s",
            task_id,
            attempt,
            duration_ms,
            exc,
        )

        if self.request.retries >= self.max_retries:
            record_dlq_entry(
                task_id=task_id,
                task_name=self.name,
                attempt=attempt,
                error_message=str(exc),
            )
            _remove_upload(input_path)
            raise

        countdown = 10 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
