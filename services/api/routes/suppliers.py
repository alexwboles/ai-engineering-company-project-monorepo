from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from tinydb import Query

try:
    from services.api.database import get_suppliers_db
    from services.api.models import (
        INITIAL_SUPPLIERS,
        SupplierCategory,
        SupplierCountry,
        SupplierCreate,
        SupplierRateUpdate,
        SupplierResponse,
        SupplierStatusUpdate,
    )
except ModuleNotFoundError:
    from database import get_suppliers_db
    from models import (
        INITIAL_SUPPLIERS,
        SupplierCategory,
        SupplierCountry,
        SupplierCreate,
        SupplierRateUpdate,
        SupplierResponse,
        SupplierStatusUpdate,
    )

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


router = APIRouter(tags=["suppliers"])


def _to_response(doc_id: int, payload: dict[str, Any]) -> SupplierResponse:
    return SupplierResponse.model_validate({"id": doc_id, **payload})


def _supplier_document(supplier: dict[str, object]) -> dict[str, object]:
    document = dict(supplier)
    document["updated_at"] = _now_utc().isoformat()
    return document


def seed_suppliers() -> int:
    """Insert the context directory once, preserving existing TinyDB records."""

    inserted = 0
    supplier_query = Query()

    with get_suppliers_db() as db:
        for supplier in INITIAL_SUPPLIERS:
            name = str(supplier["name"])
            country = str(supplier["country"])
            exists = db.search((supplier_query.name == name) & (supplier_query.country == country))
            if exists:
                continue

            # Validate the seeder payload before it reaches TinyDB.
            SupplierCreate.model_validate(supplier)
            document = _supplier_document(supplier)
            db.insert(document)
            inserted += 1

    return inserted


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def create_supplier(payload: SupplierCreate) -> SupplierResponse:
    document = {
        **payload.model_dump(mode="json"),
        "updated_at": _now_utc().isoformat(),
    }

    with get_suppliers_db() as db:
        doc_id = db.insert(document)

    return _to_response(doc_id, document)


@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(
    country: SupplierCountry | None = None,
    category: SupplierCategory | None = None,
) -> list[SupplierResponse]:
    with get_suppliers_db() as db:
        rows = db.all()

    suppliers = [_to_response(row.doc_id, dict(row)) for row in rows]

    if country:
        suppliers = [item for item in suppliers if item.country == country]

    if category:
        suppliers = [item for item in suppliers if category in item.categories]

    return suppliers


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int) -> SupplierResponse:
    with get_suppliers_db() as db:
        row = db.get(doc_id=supplier_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    return _to_response(supplier_id, dict(row))


@router.patch("/suppliers/{supplier_id}/rate", response_model=SupplierResponse)
def update_supplier_rate(supplier_id: int, payload: SupplierRateUpdate) -> SupplierResponse:
    with get_suppliers_db() as db:
        row = db.get(doc_id=supplier_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Supplier not found.")

        db.update(
            {
                "monthly_rate": payload.monthly_rate,
                "updated_at": _now_utc().isoformat(),
            },
            doc_ids=[supplier_id],
        )
        updated = db.get(doc_id=supplier_id)

    if updated is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    return _to_response(supplier_id, dict(updated))


@router.patch("/suppliers/{supplier_id}/status", response_model=SupplierResponse)
def update_supplier_status(supplier_id: int, payload: SupplierStatusUpdate) -> SupplierResponse:
    with get_suppliers_db() as db:
        row = db.get(doc_id=supplier_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Supplier not found.")

        db.update(
            {
                "status": payload.status.value,
                "updated_at": _now_utc().isoformat(),
            },
            doc_ids=[supplier_id],
        )
        updated = db.get(doc_id=supplier_id)

    if updated is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    return _to_response(supplier_id, dict(updated))


@router.delete("/suppliers/{supplier_id}", status_code=200)
def delete_supplier(supplier_id: int) -> dict[str, str]:
    with get_suppliers_db() as db:
        row = db.get(doc_id=supplier_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Supplier not found.")
        db.remove(doc_ids=[supplier_id])

    return {"message": "Supplier deleted."}
