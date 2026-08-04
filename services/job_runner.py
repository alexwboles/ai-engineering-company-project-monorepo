"""Database status control for independent nightly jobs.

This module intentionally has no web-application imports. The ``processing`` status in
``public.job_runs`` is the only distributed lock used by the nightly worker.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as exc:  # pragma: no cover - dependency is installed by services/api.
    psycopg2 = None
    RealDictCursor = None
    _PSYCOPG2_IMPORT_ERROR = exc
else:
    _PSYCOPG2_IMPORT_ERROR = None


JOB_NAME = "nightly_export"


class JobRunError(RuntimeError):
    """Raised when the job-run state cannot be persisted."""


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise JobRunError("DATABASE_URL is not configured")
    return value


def get_connection():
    """Open a short-lived PostgreSQL connection for one status operation."""

    if psycopg2 is None:
        raise JobRunError("psycopg2 is required for job-run status control") from _PSYCOPG2_IMPORT_ERROR
    return psycopg2.connect(_database_url(), connect_timeout=10)


def _as_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("target_date must use YYYY-MM-DD format") from exc


def get_job_run(job_name: str, target_date: date | str) -> dict[str, Any] | None:
    target = _as_date(target_date)
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, job_name, target_date, status, started_at, finished_at,
                       error_message, created_at
                FROM public.job_runs
                WHERE job_name = %s AND target_date = %s
                """,
                (job_name, target),
            )
            row = cursor.fetchone()
            connection.commit()
            return dict(row) if row is not None else None


def create_job_run(job_name: str, target_date: date | str) -> dict[str, Any]:
    """Create the idempotency record in ``pending`` before work begins."""

    target = _as_date(target_date)
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO public.job_runs (job_name, target_date, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (job_name, target_date) DO NOTHING
                """,
                (job_name, target),
            )
            cursor.execute(
                """
                SELECT id, job_name, target_date, status, started_at, finished_at,
                       error_message, created_at
                FROM public.job_runs
                WHERE job_name = %s AND target_date = %s
                """,
                (job_name, target),
            )
            row = cursor.fetchone()
            connection.commit()
    if row is None:  # pragma: no cover - protected by the unique key and transaction.
        raise JobRunError("Unable to create or load the nightly job run")
    return dict(row)


def update_job_run(run_id: str, status: str, error_message: str | None = None) -> bool:
    """Update a job state using only the four states in the schema contract."""

    if status not in {"pending", "processing", "completed", "failed"}:
        raise ValueError("Unsupported job run status")
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if status == "processing":
                cursor.execute(
                    """
                    UPDATE public.job_runs
                    SET status = %s, started_at = %s,
                        finished_at = NULL, error_message = NULL
                    WHERE id = %s
                    """,
                    (status, now, run_id),
                )
            elif status in {"completed", "failed"}:
                cursor.execute(
                    """
                    UPDATE public.job_runs
                    SET status = %s, finished_at = %s, error_message = %s
                    WHERE id = %s
                    """,
                    (status, now, error_message, run_id),
                )
            else:
                cursor.execute(
                    "UPDATE public.job_runs SET status = %s WHERE id = %s",
                    (status, run_id),
                )
            updated = cursor.rowcount == 1
            connection.commit()
    return updated


def has_processing_lock(job_name: str = JOB_NAME) -> bool:
    """Return whether another target date is currently running this job."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM public.job_runs
                    WHERE job_name = %s AND status = 'processing'
                )
                """,
                (job_name,),
            )
            result = cursor.fetchone()
            connection.commit()
    return bool(result and result[0])


def has_completed_for_date(job_name: str, target_date: date | str) -> bool:
    """Return whether this exact job/date already completed successfully."""

    target = _as_date(target_date)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM public.job_runs
                    WHERE job_name = %s AND target_date = %s AND status = 'completed'
                )
                """,
                (job_name, target),
            )
            result = cursor.fetchone()
            connection.commit()
    return bool(result and result[0])


def mark_processing(run_id: str) -> bool:
    """Atomically claim a pending/failed row as the one processing run."""

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.job_runs
                SET status = 'processing', started_at = %s,
                    finished_at = NULL, error_message = NULL
                WHERE id = %s AND status IN ('pending', 'failed')
                """,
                (datetime.now(timezone.utc), run_id),
            )
            claimed = cursor.rowcount == 1
            connection.commit()
            return claimed
    except Exception as exc:
        connection.rollback()
        if psycopg2 is not None and isinstance(exc, psycopg2.IntegrityError):
            # The unique processing index means another process won the lock.
            return False
        raise
    finally:
        connection.close()


def mark_completed(run_id: str) -> bool:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.job_runs
                SET status = 'completed', finished_at = %s, error_message = NULL
                WHERE id = %s AND status = 'processing'
                """,
                (datetime.now(timezone.utc), run_id),
            )
            completed = cursor.rowcount == 1
            connection.commit()
            return completed
    finally:
        connection.close()


def mark_failed(run_id: str, error: BaseException) -> None:
    message = str(error).strip() or type(error).__name__
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.job_runs
                SET status = 'failed', finished_at = %s, error_message = %s
                WHERE id = %s AND status = 'processing'
                """,
                (datetime.now(timezone.utc), message[:2000], run_id),
            )
            connection.commit()
