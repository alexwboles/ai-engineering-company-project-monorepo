from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from services.api import main
from services.api.incident_analysis import analyze_incident_csv_text, load_and_analyze_csv


ROOT = Path(__file__).resolve().parents[3]
HEALTHCORE_SAMPLE = ROOT / "scripts" / "incidents-healthcore.csv"


def test_healthcore_sample_matches_context_targets() -> None:
    summary, invalid_records, _ = load_and_analyze_csv(HEALTHCORE_SAMPLE)

    assert summary.total_records == 100
    assert summary.valid_records == 94
    assert summary.invalid_records == 6
    assert summary.average_satisfaction_closed == 3.58
    assert summary.category_breakdown == {"APPOINTMENT": 47, "BILLING": 47}
    assert summary.country_breakdown == {"UK": 37, "US": 57}
    assert {issue.reason for issue in invalid_records} == {
        "invalid_clinic_id",
        "clinic_country_mismatch",
        "invalid_patient_id",
        "invalid_category",
        "invalid_status",
        "missing_required_field",
    }


def test_domain_validation_rejects_phi_and_missing_closed_score() -> None:
    csv_text = (
        "incident_id,created_at,clinic_id,country,patient_id,category,status,satisfaction_score,patient_email\n"
        "INC-1,2026-07-01,us-tx-001,US,HC-ABC123,BILLING,CLOSED,,\n"
        "INC-2,2026-07-01,us-tx-001,US,HC-ABC124,BILLING,OPEN,,person@example.com\n"
    )

    summary, invalid_records, _ = analyze_incident_csv_text(csv_text)

    assert summary.valid_records == 0
    assert summary.invalid_records == 2
    assert {issue.reason for issue in invalid_records} == {
        "missing_satisfaction_score",
        "forbidden_phi_field",
    }
    assert all("person@example.com" not in issue.details for issue in invalid_records)


def test_cli_healthcore_sample_verifies_and_exits_successfully() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "analyze.py"), str(HEALTHCORE_SAMPLE)],
        input="n\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Valid records           : 94" in result.stdout
    assert "Invalid records         : 6" in result.stdout
    assert "Average satisfaction (closed with score): 3.5800" in result.stdout
    assert "Verification result: OK" in result.stdout


def test_analysis_endpoint_returns_healthcore_summary_and_export() -> None:
    main.app.dependency_overrides[main.get_current_user] = lambda: object()
    csv_bytes = HEALTHCORE_SAMPLE.read_bytes()
    try:
        client = TestClient(main.app)
        response = client.post(
            "/api/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", csv_bytes, "text/csv")},
        )
        export = client.get("/api/incidents/results/export")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["valid_records"] == 94
    assert response.json()["summary"]["invalid_records"] == 6
    assert response.json()["summary"]["average_satisfaction_closed"] == 3.58
    assert export.status_code == 200
    assert "clinic.us-tx-001" in export.text
