from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

try:
    # Works when imported as services.api.main from repository root.
    from services.api.incident_analysis import (
        analyze_incident_rows,
        now_iso,
        summary_to_csv_text,
        summary_to_dict,
    )
except ModuleNotFoundError:
    # Works when running uvicorn from services/api with module path main:app.
    from incident_analysis import analyze_incident_rows, now_iso, summary_to_csv_text, summary_to_dict

app = FastAPI(title="HealthCore Incident Analysis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_analysis_summary_csv: str | None = None
_last_analysis_payload: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/incidents/analyze")
async def analyze_incidents(file: UploadFile = File(...)) -> dict[str, Any]:
    global _last_analysis_payload
    global _last_analysis_summary_csv

    if not file.filename:
        raise HTTPException(status_code=400, detail="A CSV file is required.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .csv file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("CSV header row is missing.")
        summary, invalid_records, _valid_rows = analyze_incident_rows(reader)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to process CSV: {exc}") from exc

    payload = {
        "generated_at": now_iso(),
        "summary": summary_to_dict(summary),
        "invalid_records": [asdict(issue) for issue in invalid_records],
    }

    _last_analysis_payload = payload
    _last_analysis_summary_csv = summary_to_csv_text(summary)

    return payload


@app.get("/api/incidents/results/export")
def export_last_results() -> Response:
    if _last_analysis_summary_csv is None:
        raise HTTPException(status_code=404, detail="No analysis available to export yet.")

    return Response(
        content=_last_analysis_summary_csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )
