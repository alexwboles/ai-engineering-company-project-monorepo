from __future__ import annotations

from pathlib import Path

from tinydb import TinyDB

SUPPLIERS_DB_PATH = Path(__file__).resolve().parent / "data" / "suppliers.json"


def get_suppliers_db() -> TinyDB:
    SUPPLIERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(SUPPLIERS_DB_PATH, indent=2, ensure_ascii=True)
