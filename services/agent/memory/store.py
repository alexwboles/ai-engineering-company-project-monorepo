"""SQLite-backed persistent memory with a small explicit CRUD interface."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import MemoryProposal
from .policy import is_forbidden_memory


class MemoryPolicyError(ValueError):
    """Raised when a caller attempts to persist forbidden HealthCore data."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class MemoryStore:
    """Persistent memory interface; all writes are explicit and auditable."""

    def __init__(self, path: str | Path, *, ttl_days: int = 90, max_entries: int = 100) -> None:
        self.path = Path(path)
        self.ttl_days = ttl_days
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    memory_key TEXT PRIMARY KEY,
                    fact TEXT NOT NULL,
                    keys_json TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_proposals (
                    session_id TEXT PRIMARY KEY,
                    proposal_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    proposed_fact TEXT NOT NULL,
                    originating_message TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    written INTEGER NOT NULL,
                    reason TEXT NOT NULL
                );
                """
            )

    def read(self, memory_key: str | None = None) -> list[dict[str, Any]]:
        """Read active entries, optionally selecting one deterministic key."""

        self.consolidate()
        with self._connect() as connection:
            if memory_key:
                rows = connection.execute(
                    "SELECT * FROM memory_entries WHERE memory_key = ?",
                    (memory_key,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM memory_entries ORDER BY updated_at DESC"
                ).fetchall()
        return [self._entry(row) for row in rows]

    def read_relevant(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve a small lexical set of approved facts for the current turn."""

        tokens = {token for token in query.casefold().split() if len(token) > 2}
        scored: list[tuple[int, dict[str, Any]]] = []
        for entry in self.read():
            haystack = f"{entry['fact']} {' '.join(entry['keys'])}".casefold()
            score = sum(token in haystack for token in tokens)
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1]["updated_at"]))
        return [entry for _, entry in scored[:limit]]

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.read()[:limit]

    def write(self, proposal: MemoryProposal, *, ttl_days: int | None = None) -> dict[str, Any]:
        """Upsert one approved proposal; forbidden content cannot be persisted."""

        if is_forbidden_memory(proposal.fact):
            raise MemoryPolicyError("The proposed fact violates HealthCore memory policy.")
        now = _now()
        expires = now + timedelta(days=ttl_days if ttl_days is not None else self.ttl_days)
        memory_key = self._memory_key(proposal)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_entries
                    (memory_key, fact, keys_json, proposal_id, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_key) DO UPDATE SET
                    fact = excluded.fact,
                    keys_json = excluded.keys_json,
                    proposal_id = excluded.proposal_id,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                (
                    memory_key,
                    proposal.fact,
                    json.dumps(list(proposal.keys)),
                    proposal.proposal_id,
                    _iso(now),
                    _iso(now),
                    _iso(expires),
                ),
            )
        return {"memory_key": memory_key, "fact": proposal.fact, "keys": list(proposal.keys)}

    def delete(self, memory_key: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM memory_entries WHERE memory_key = ?", (memory_key,))
        return cursor.rowcount > 0

    def set_pending(self, session_id: str, proposal: MemoryProposal) -> bool:
        """Set at most one pending proposal per conversation session."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO pending_proposals (session_id, proposal_json, created_at)
                VALUES (?, ?, ?)
                """,
                (session_id, json.dumps(proposal.as_dict()), _iso(_now())),
            )
        return cursor.rowcount == 1

    def get_pending(self, session_id: str) -> MemoryProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT proposal_json FROM pending_proposals WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["proposal_json"])
        return MemoryProposal(
            proposal_id=str(payload["proposal_id"]),
            action="upsert",
            fact=str(payload["fact"]),
            reason=str(payload["reason"]),
            keys=tuple(str(key) for key in payload["keys"]),
        )

    def clear_pending(self, session_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM pending_proposals WHERE session_id = ?", (session_id,))

    def audit(
        self,
        *,
        proposal: MemoryProposal,
        originating_message: str,
        user_message: str,
        decision: str,
        written: bool,
        reason: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_audit
                    (timestamp, proposal_id, proposed_fact, originating_message,
                     user_message, decision, written, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _iso(_now()),
                    proposal.proposal_id,
                    proposal.fact,
                    originating_message,
                    user_message,
                    decision,
                    int(written),
                    reason,
                ),
            )

    def audit_entries(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM memory_audit ORDER BY audit_id").fetchall()
        return [dict(row) for row in rows]

    def consolidate(self) -> dict[str, int]:
        """Apply TTL expiry and a hard cap; topic-key upserts deduplicate facts."""

        now = _iso(_now())
        with self._connect() as connection:
            expired = connection.execute(
                "DELETE FROM memory_entries WHERE expires_at <= ?", (now,)
            ).rowcount
            rows = connection.execute(
                "SELECT memory_key FROM memory_entries ORDER BY updated_at DESC"
            ).fetchall()
            excess = max(0, len(rows) - self.max_entries)
            for row in rows[self.max_entries :]:
                connection.execute("DELETE FROM memory_entries WHERE memory_key = ?", (row["memory_key"],))
        return {"expired": expired, "evicted": excess}

    @staticmethod
    def _memory_key(proposal: MemoryProposal) -> str:
        topic = "|".join(sorted(proposal.keys))
        return "healthcore:" + hashlib.sha256(topic.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _entry(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "memory_key": row["memory_key"],
            "fact": row["fact"],
            "keys": json.loads(row["keys_json"]),
            "proposal_id": row["proposal_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
        }


_DEFAULT_STORE: MemoryStore | None = None


def get_default_memory_store() -> MemoryStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        path = os.getenv("HEALTHCORE_MEMORY_DB", "data/memory/healthcore_memory.sqlite3")
        _DEFAULT_STORE = MemoryStore(path)
    return _DEFAULT_STORE
