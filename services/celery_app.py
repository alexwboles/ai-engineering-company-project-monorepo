"""Celery application shared by the API producer and worker processes."""

from __future__ import annotations

import os

from celery import Celery


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "healthcore",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=("services.tasks.report_tasks",),
)

celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    result_expires=86400,
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    task_soft_time_limit=240,
    task_time_limit=300,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
