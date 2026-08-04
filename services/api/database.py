from __future__ import annotations

import logging
import os
from collections.abc import Generator
from pathlib import Path

from fastapi import HTTPException, status
from tinydb import TinyDB
from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger("healthcore.database")

SUPPLIERS_DB_PATH = Path(__file__).resolve().parent / "data" / "suppliers.json"
AUTH_DB_PATH = Path(__file__).resolve().parent / "data" / "auth.json"
INCIDENTS_DB_PATH = Path(__file__).resolve().parent / "data" / "incidents.json"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# TinyDB remains the auth/profile store. SQLModel owns inventory data in
# Supabase, with one request-scoped session rather than a global session.
inventory_engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


def get_suppliers_db() -> TinyDB:
    SUPPLIERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(SUPPLIERS_DB_PATH, indent=2, ensure_ascii=True)


def get_auth_db() -> TinyDB:
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(AUTH_DB_PATH, indent=2, ensure_ascii=True)


def get_incidents_db() -> TinyDB:
    INCIDENTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(INCIDENTS_DB_PATH, indent=2, ensure_ascii=True)


def get_db() -> Generator[Session, None, None]:
    """Yield one SQLModel session for an inventory request."""

    if inventory_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inventory database is not configured.",
        )

    with Session(inventory_engine) as session:
        yield session


def init_inventory_db() -> None:
    """Create SQLModel tables in Supabase when a database URL is configured."""

    if inventory_engine is None:
        logger.warning("DATABASE_URL is absent; inventory schema initialization skipped")
        return

    SQLModel.metadata.create_all(inventory_engine)
