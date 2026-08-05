from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from starlette.requests import Request

try:
    from services.api.auth_security import get_current_user
    from services.api.database import init_inventory_db
    from services.api.routes import (
        auth_router,
        incidents_router,
        inventory_router,
        profiles_router,
        suppliers_router,
        telemetry_router,
        telemetry_report_router,
        tasks_router,
        rfp_router,
        agent_router,
        knowledge_router,
        users_router,
    )
except ModuleNotFoundError:
    from auth_security import get_current_user
    from database import init_inventory_db
    from routes import (
        auth_router,
        incidents_router,
        inventory_router,
        profiles_router,
        suppliers_router,
        telemetry_report_router,
        telemetry_router,
        tasks_router,
        rfp_router,
        agent_router,
        knowledge_router,
        users_router,
    )

try:
    from services.api.telemetry_storage import create_telemetry_store
except ModuleNotFoundError:
    from telemetry_storage import create_telemetry_store

try:
    from services.reporting.routes import router as reporting_router
except ModuleNotFoundError:
    from reporting.routes import router as reporting_router

try:
    from services.tasks.report_tasks import analyze_incident_csv
except ModuleNotFoundError:
    from tasks.report_tasks import analyze_incident_csv

logger = logging.getLogger("healthcore.api")
TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events")

app = FastAPI(title="HealthCore Incident Analysis API", version="1.0.0")
app.state.telemetry_endpoint = TELEMETRY_ENDPOINT
app.state.telemetry_store = create_telemetry_store()
app.state.telemetry_reader = app.state.telemetry_store

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TASK_INPUT_DIR = Path(__file__).resolve().parent / "data" / "celery_tasks"
LATEST_RESULTS_CSV = TASK_INPUT_DIR / "results" / "latest_results.csv"

app.include_router(suppliers_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(telemetry_router)
app.include_router(telemetry_report_router)
app.include_router(inventory_router)
app.include_router(reporting_router)
app.include_router(tasks_router)
app.include_router(rfp_router)
app.include_router(agent_router)
app.include_router(knowledge_router)


@app.on_event("startup")
def initialize_inventory_schema() -> None:
    init_inventory_db()


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
) -> JSONResponse:
    _ = current_user

    if not file.filename:
        raise HTTPException(status_code=400, detail="A CSV file is required.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .csv file.")

    TASK_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_path = TASK_INPUT_DIR / f"{uuid.uuid4().hex}.csv"

    try:
        with input_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                destination.write(chunk)
    except OSError:
        input_path.unlink(missing_ok=True)
        logger.exception("Failed to stage uploaded CSV file")
        raise HTTPException(status_code=400, detail="Unable to stage the uploaded file.") from None
    finally:
        await file.close()

    if input_path.stat().st_size == 0:
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        task = analyze_incident_csv.delay(str(input_path))
    except Exception:
        input_path.unlink(missing_ok=True)
        logger.exception("Unable to enqueue incident CSV analysis")
        raise HTTPException(
            status_code=503,
            detail="The analysis queue is temporarily unavailable. Please try again.",
        ) from None

    return JSONResponse(status_code=202, content={"task_id": task.id})


@app.get("/api/incidents/results/export")
def export_last_results(current_user=Depends(get_current_user)) -> Response:
    _ = current_user
    if not LATEST_RESULTS_CSV.exists():
        raise HTTPException(status_code=404, detail="No analysis available to export yet.")

    return Response(
        content=LATEST_RESULTS_CSV.read_text(encoding="utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )
