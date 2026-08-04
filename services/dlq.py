"""Persistence for Celery tasks that exhaust their retry budget."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import psycopg2


logger = logging.getLogger("healthcore.dlq")


def record_dlq_entry(*, task_id: str, task_name: str, attempt: int, error_message: str) -> None:
    """Record the final task failure without masking the original exception."""

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        logger.error(
            "DLQ persistence skipped: DATABASE_URL is not configured task_id=%s attempt=%s",
            task_id,
            attempt,
        )
        return

    try:
        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO dlq_tasks (task_id, task_name, attempt, error_message, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET
                        attempt = EXCLUDED.attempt,
                        error_message = EXCLUDED.error_message,
                        created_at = EXCLUDED.created_at
                    """,
                    (
                        task_id,
                        task_name,
                        attempt,
                        error_message,
                        datetime.now(timezone.utc),
                    ),
                )
            connection.commit()
    except Exception:
        # DLQ recording is best effort; the task's final failure must still be
        # visible to Celery and must not be replaced by a database exception.
        logger.exception("Unable to persist DLQ entry task_id=%s attempt=%s", task_id, attempt)
