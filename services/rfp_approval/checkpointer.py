"""Durable SQLite checkpoint and trace storage for approval branches."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_checkpoint_path() -> Path:
    configured = os.getenv("RFP_APPROVAL_CHECKPOINT_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "services" / "api" / "data" / "rfp_approval_checkpoints.sqlite3"


class ApprovalCheckpointer:
    """A small process-safe checkpointer; each operation uses its own SQLite connection."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_checkpoint_path()
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rfp_approval_checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rfp_approval_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    ticket_id TEXT NOT NULL,
                    node TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rfp_approval_trace_thread
                    ON rfp_approval_trace(thread_id, id);
                """
            )

    def save_state(self, state: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(state, ensure_ascii=True, sort_keys=True)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO rfp_approval_checkpoints(thread_id, ticket_id, state_json, status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (state["thread_id"], state["ticket_id"], payload, state["status"], now),
            )

    def load_state(self, thread_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM rfp_approval_checkpoints WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return json.loads(row["state_json"]) if row else None

    def append_trace(
        self,
        *,
        thread_id: str,
        ticket_id: str,
        node: str,
        agent: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        trace = {
            "ts": timestamp,
            "agent": agent,
            "node": node,
            "input": input_data,
            "output": output_data,
            "input_ref": f"{node}:input",
            "output_ref": f"{node}:output",
        }
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO rfp_approval_trace(
                    thread_id, ticket_id, node, agent, input_json, output_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    ticket_id,
                    node,
                    agent,
                    json.dumps(input_data, ensure_ascii=True, sort_keys=True),
                    json.dumps(output_data, ensure_ascii=True, sort_keys=True),
                    timestamp,
                ),
            )
        return trace

    def get_trace(self, thread_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT node, agent, input_json, output_json, timestamp
                FROM rfp_approval_trace WHERE thread_id = ? ORDER BY id
                """,
                (thread_id,),
            ).fetchall()
        return [
            {
                "node": row["node"],
                "agent": row["agent"],
                "input": json.loads(row["input_json"]),
                "output": json.loads(row["output_json"]),
                "ts": row["timestamp"],
            }
            for row in rows
        ]
