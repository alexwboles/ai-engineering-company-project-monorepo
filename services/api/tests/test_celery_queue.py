from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api import main
from services.celery_app import celery_app
from services.tasks import report_tasks
from services.tasks.report_tasks import analyze_incident_csv


def test_incident_analysis_task_is_configured_for_retries_and_timeouts() -> None:
    assert analyze_incident_csv.max_retries == 3
    assert analyze_incident_csv.soft_time_limit == 240
    assert analyze_incident_csv.time_limit == 300
    assert list(inspect.signature(analyze_incident_csv.run).parameters) == ["csv_path"]


def test_incident_analysis_task_processes_a_file_path_without_inline_payload(
    tmp_path: Path, monkeypatch
) -> None:
    csv_path = tmp_path / "incidents.csv"
    csv_path.write_text(
        "incident_id,created_at,customer_id,category,status,satisfaction_index\n"
        "INC-1,2026-08-04,CUST-1,complaint,closed,5\n",
        encoding="utf-8",
    )

    monkeypatch.setitem(celery_app.conf, "task_always_eager", True)
    result = analyze_incident_csv.apply(args=[str(csv_path)], task_id="task-success")

    assert result.successful()
    assert result.result["summary"]["valid_records"] == 1
    assert not csv_path.exists()
    assert (tmp_path / "results" / "latest_results.csv").exists()


def test_task_status_endpoint_maps_celery_states(monkeypatch) -> None:
    tasks_module = importlib.import_module("services.api.routes.tasks")

    class FakeResult:
        status = "SUCCESS"
        result = {"summary": {"valid_records": 1}}

    monkeypatch.setattr(tasks_module, "AsyncResult", lambda _task_id, app: FakeResult())

    response = tasks_module.get_task_status("task-success")

    assert response == {
        "task_id": "task-success",
        "status": "success",
        "result": {"summary": {"valid_records": 1}},
    }


def test_analysis_endpoint_enqueues_and_returns_202(monkeypatch) -> None:
    class FakeTask:
        id = "task-enqueued"

    monkeypatch.setattr(main.analyze_incident_csv, "delay", lambda _path: FakeTask())
    main.app.dependency_overrides[main.get_current_user] = lambda: object()

    try:
        response = TestClient(main.app).post(
            "/api/incidents/analyze",
            files={"file": ("incidents.csv", b"incident_id\nINC-1\n", "text/csv")},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-enqueued"}


def test_final_retry_records_dlq_entry(monkeypatch, tmp_path: Path) -> None:
    csv_path = tmp_path / "failed.csv"
    csv_path.write_text("not-used\n", encoding="utf-8")
    entries: list[dict[str, object]] = []

    def raise_processing_error(_path: Path):
        raise RuntimeError("temporary analysis dependency failed")

    monkeypatch.setattr(report_tasks, "load_and_analyze_csv", raise_processing_error)
    monkeypatch.setattr(report_tasks, "record_dlq_entry", lambda **entry: entries.append(entry))

    analyze_incident_csv.push_request(id="task-failed", retries=3)
    try:
        with pytest.raises(RuntimeError, match="temporary analysis dependency failed"):
            analyze_incident_csv.run(str(csv_path))
    finally:
        analyze_incident_csv.pop_request()

    assert entries == [
        {
            "task_id": "task-failed",
            "task_name": "healthcore.analyze_incident_csv",
            "attempt": 4,
            "error_message": "temporary analysis dependency failed",
        }
    ]
