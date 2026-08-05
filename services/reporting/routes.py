from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

try:
    from services.api.auth_security import get_current_user
except ModuleNotFoundError:
    from auth_security import get_current_user

try:
    from data.pipelines.pipeline import (
        get_latest_pipeline_run,
        monthly_clinic_supply_backfill_flow,
        read_monthly_report,
    )
except ModuleNotFoundError:
    from pipeline import get_latest_pipeline_run, monthly_clinic_supply_backfill_flow, read_monthly_report


router = APIRouter(prefix="/reporting", tags=["reporting"])


class MonthlyClinicSupplyReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month_start: str | None
    clinics: list[dict[str, Any]]


class PipelineRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month_start: date | None = None


class PipelineRunStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    flow_name: str
    trigger_type: str
    requested_month_start: str
    started_at: str
    ended_at: str | None
    status: str
    checkpoint: str
    records_extracted: int
    records_processed: int
    records_published: int
    records_rejected: int
    source_max_timestamp: str | None
    error_code: str | None
    error_message: str | None


@router.get("/monthly-clinic-supply-performance", response_model=MonthlyClinicSupplyReport)
def get_monthly_clinic_supply_performance(
    month_start: date | None = Query(default=None),
    _current_user: Any = Depends(get_current_user),
) -> MonthlyClinicSupplyReport:
    try:
        payload = read_monthly_report(month_start.isoformat() if month_start else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Business performance reporting is temporarily unavailable.",
        ) from None
    return MonthlyClinicSupplyReport.model_validate(payload)


@router.get("/pipeline-runs/latest", response_model=PipelineRunStatus)
def get_latest_pipeline_run_status(
    _current_user: Any = Depends(get_current_user),
) -> PipelineRunStatus:
    try:
        payload = get_latest_pipeline_run()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline status is temporarily unavailable.",
        ) from None
    if payload is None:
        raise HTTPException(status_code=404, detail="No business performance pipeline run exists yet.")
    return PipelineRunStatus.model_validate(payload)


@router.post("/pipeline-runs", response_model=PipelineRunStatus, status_code=status.HTTP_202_ACCEPTED)
def trigger_pipeline_run(
    payload: PipelineRunRequest,
    _current_user: Any = Depends(get_current_user),
) -> PipelineRunStatus:
    try:
        result = monthly_clinic_supply_backfill_flow(
            month_start=payload.month_start.isoformat() if payload.month_start else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to complete the requested pipeline run.",
        ) from None
    return PipelineRunStatus.model_validate(result)
