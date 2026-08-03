from __future__ import annotations

import csv
import io
import logging
import os
from dataclasses import asdict
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from starlette.requests import Request

try:
    from services.api.auth_security import get_current_user
    from services.api.routes import (
        auth_router,
        incidents_router,
        profiles_router,
        suppliers_router,
        telemetry_router,
        users_router,
    )
except ModuleNotFoundError:
    from auth_security import get_current_user
    from routes import auth_router, incidents_router, profiles_router, suppliers_router, telemetry_router, users_router

try:
    from services.api.telemetry_storage import create_telemetry_store
except ModuleNotFoundError:
    from telemetry_storage import create_telemetry_store

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

logger = logging.getLogger("healthcore.api")
TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events")

app = FastAPI(title="HealthCore Incident Analysis API", version="1.0.0")
app.state.telemetry_endpoint = TELEMETRY_ENDPOINT
app.state.telemetry_store = create_telemetry_store()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_analysis_summary_csv: str | None = None
_last_analysis_payload: dict[str, Any] | None = None

app.include_router(suppliers_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(telemetry_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[dict[str, object]] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = str(loc[-1]) if loc else "field"
        details.append(
            {
                "loc": ["body", field],
                "msg": f"{field.replace('_', ' ').title()} is invalid.",
                "type": "value_error",
            }
        )

    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API exception: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/incidents/analyze")
async def analyze_incidents(
    file: UploadFile = File(...), current_user=Depends(get_current_user)
) -> dict[str, Any]:
    _ = current_user
    global _last_analysis_payload
    global _last_analysis_summary_csv

    if not file.filename:
        raise HTTPException(status_code=400, detail="A CSV file is required.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .csv file.")

    try:
        content = await file.read()
    except OSError:
        logger.exception("Failed to read uploaded CSV file")
        raise HTTPException(status_code=400, detail="Unable to read the uploaded file.") from None

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
    except (csv.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to process CSV. Please check the file format and try again.",
        ) from exc

    try:
        summary, invalid_records, _valid_rows = analyze_incident_rows(reader)
    except Exception:
        logger.exception("Incident CSV analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to analyze the uploaded CSV right now. Please try again.",
        ) from None

    payload = {
        "generated_at": now_iso(),
        "summary": summary_to_dict(summary),
        "invalid_records": [asdict(issue) for issue in invalid_records],
    }

    _last_analysis_payload = payload
    _last_analysis_summary_csv = summary_to_csv_text(summary)

    return payload


@app.get("/api/incidents/results/export")
def export_last_results(current_user=Depends(get_current_user)) -> Response:
    _ = current_user
    if _last_analysis_summary_csv is None:
        raise HTTPException(status_code=404, detail="No analysis available to export yet.")

    return Response(
        content=_last_analysis_summary_csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )
