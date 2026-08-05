from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tinydb import Query

try:
    from services.api.database import get_incidents_db
except ModuleNotFoundError:
    from database import get_incidents_db

try:
    from packages.shared.incident_manager_validation import (
        INCIDENT_ALLOWED_CATEGORIES,
        INCIDENT_ALLOWED_ORIGINS,
        INCIDENT_ALLOWED_STATUSES,
    )
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from packages.shared.incident_manager_validation import (  # type: ignore
        INCIDENT_ALLOWED_CATEGORIES,
        INCIDENT_ALLOWED_ORIGINS,
        INCIDENT_ALLOWED_STATUSES,
    )


class IncidentsService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _to_response(doc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": doc_id,
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "category": payload.get("category", ""),
            "status": payload.get("status", ""),
            "origin": payload.get("origin", ""),
            "branch": payload.get("branch", ""),
            "created_at": payload.get("created_at", ""),
            "updated_at": payload.get("updated_at", ""),
        }

    @staticmethod
    def create_incident(payload: dict[str, str]) -> dict[str, Any]:
        now = IncidentsService._now_iso()
        row = {
            "title": payload["title"],
            "description": payload["description"],
            "category": payload["category"],
            "status": payload["status"],
            "origin": payload["origin"],
            "branch": payload["branch"],
            "created_at": now,
            "updated_at": now,
        }

        with get_incidents_db() as db:
            incidents = db.table("incidents")
            doc_id = incidents.insert(row)
            inserted = incidents.get(doc_id=doc_id)

        assert inserted is not None
        return IncidentsService._to_response(doc_id, inserted)

    @staticmethod
    def upsert_seed_incident(payload: dict[str, str], source_incident_id: str) -> tuple[dict[str, Any], bool]:
        now = IncidentsService._now_iso()
        incident_query = Query()

        with get_incidents_db() as db:
            incidents = db.table("incidents")
            existing = incidents.get(incident_query.source_incident_id == source_incident_id)
            if existing is not None:
                return IncidentsService._to_response(existing.doc_id, existing), False

            row = {
                "title": payload["title"],
                "description": payload["description"],
                "category": payload["category"],
                "status": payload["status"],
                "origin": payload["origin"],
                "branch": payload["branch"],
                "created_at": payload["created_at"],
                "updated_at": now,
                "source_incident_id": source_incident_id,
            }
            doc_id = incidents.insert(row)
            inserted = incidents.get(doc_id=doc_id)

        assert inserted is not None
        return IncidentsService._to_response(doc_id, inserted), True

    @staticmethod
    def list_incidents(
        *,
        status: str | None = None,
        origin: str | None = None,
        branch: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        with get_incidents_db() as db:
            incidents = db.table("incidents")
            rows = incidents.all()

        filtered: list[dict[str, Any]] = []
        for row in rows:
            if status and row.get("status") != status:
                continue
            if origin and row.get("origin") != origin:
                continue
            if branch and row.get("branch") != branch:
                continue
            if category and row.get("category") != category:
                continue
            filtered.append(IncidentsService._to_response(row.doc_id, row))

        filtered.sort(key=lambda item: (str(item.get("created_at", "")), int(item.get("id", 0))), reverse=True)
        return filtered

    @staticmethod
    def get_incident_by_id(incident_id: int) -> dict[str, Any] | None:
        with get_incidents_db() as db:
            incidents = db.table("incidents")
            row = incidents.get(doc_id=incident_id)

        if row is None:
            return None

        return IncidentsService._to_response(row.doc_id, row)

    @staticmethod
    def update_incident_status(incident_id: int, status: str) -> dict[str, Any] | None:
        now = IncidentsService._now_iso()

        with get_incidents_db() as db:
            incidents = db.table("incidents")
            row = incidents.get(doc_id=incident_id)
            if row is None:
                return None

            incidents.update({"status": status, "updated_at": now}, doc_ids=[incident_id])
            updated = incidents.get(doc_id=incident_id)

        if updated is None:
            return None

        return IncidentsService._to_response(incident_id, updated)

    @staticmethod
    def get_summary() -> dict[str, Any]:
        by_status = {status: 0 for status in INCIDENT_ALLOWED_STATUSES}
        by_origin = {origin: 0 for origin in INCIDENT_ALLOWED_ORIGINS}
        by_category = {category: 0 for category in INCIDENT_ALLOWED_CATEGORIES}
        by_branch: dict[str, int] = {}

        with get_incidents_db() as db:
            incidents = db.table("incidents")
            rows = incidents.all()

        for row in rows:
            status = str(row.get("status", ""))
            origin = str(row.get("origin", ""))
            category = str(row.get("category", ""))
            branch = str(row.get("branch", ""))

            if status in by_status:
                by_status[status] += 1
            else:
                by_status[status] = by_status.get(status, 0) + 1

            if origin in by_origin:
                by_origin[origin] += 1
            else:
                by_origin[origin] = by_origin.get(origin, 0) + 1

            if category in by_category:
                by_category[category] += 1
            else:
                by_category[category] = by_category.get(category, 0) + 1

            by_branch[branch] = by_branch.get(branch, 0) + 1

        return {
            "total_incidents": len(rows),
            "total_by_status": by_status,
            "total_by_category": by_category,
            "total_by_origin": by_origin,
            "total_by_branch": dict(sorted(by_branch.items())),
        }
