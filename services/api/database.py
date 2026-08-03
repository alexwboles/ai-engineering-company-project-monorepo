from __future__ import annotations

from pathlib import Path

from tinydb import TinyDB

SUPPLIERS_DB_PATH = Path(__file__).resolve().parent / "data" / "suppliers.json"
AUTH_DB_PATH = Path(__file__).resolve().parent / "data" / "auth.json"
INCIDENTS_DB_PATH = Path(__file__).resolve().parent / "data" / "incidents.json"


def get_suppliers_db() -> TinyDB:
    SUPPLIERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(SUPPLIERS_DB_PATH, indent=2, ensure_ascii=True)


def get_auth_db() -> TinyDB:
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(AUTH_DB_PATH, indent=2, ensure_ascii=True)


def get_incidents_db() -> TinyDB:
    INCIDENTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(INCIDENTS_DB_PATH, indent=2, ensure_ascii=True)
