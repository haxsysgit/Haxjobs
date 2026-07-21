"""Append-only session persistence — stdlib sqlite3, foreign keys on, WAL for files.

Plan 003 Phase 4: Persist canonical conversation messages at durable boundaries
and resume after process exit.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from haxjobs.agent_core.messages import (
    AssistantMessage,
    ConversationMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_DDL = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_messages (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL,
    message_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class SessionStore:
    """Append-only SQLite store for session messages.

    - plain stdlib sqlite3
    - foreign keys on
    - WAL for file-backed databases (not :memory:)
    - append-only messages
    - deterministic sequence order via AUTOINCREMENT
    - local DB file mode 0600
    """

    def __init__(self, db_path: str | Path) -> None:
        db_path = Path(db_path)
        is_memory = str(db_path) == ":memory:"
        if not is_memory:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = _row_factory
        if not is_memory:
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_DDL)
        if not is_memory:
            db_path.chmod(0o600)

    def close(self) -> None:
        self._conn.close()

    def create_session(self, session_id: str) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO sessions (session_id, created_at, updated_at, status, turn_count) "
            "VALUES (?, ?, ?, 'active', 0)",
            (session_id, now, now),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def latest_session_id(self) -> str | None:
        row = self._conn.execute(
            "SELECT session_id FROM sessions ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        return row["session_id"] if row else None

    def append_message(self, session_id: str, message: ConversationMessage) -> None:
        """Append one canonical message. Uses deterministic sequence via AUTOINCREMENT."""
        now = _now()
        payload = message.model_dump()
        payload_json = json.dumps(payload, default=str)
        self._conn.execute(
            "INSERT INTO session_messages (session_id, turn_id, message_kind, "
            "payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, message.turn_id, message.kind, payload_json, now),
        )
        # Update session updated_at
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        self._conn.commit()

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Return all messages for a session in deterministic sequence order.

        Each row includes: sequence, session_id, turn_id, message_kind,
        payload_json (parsed as dict), created_at.
        """
        rows = self._conn.execute(
            "SELECT * FROM session_messages WHERE session_id = ? ORDER BY sequence",
            (session_id,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            try:
                d["payload_json"] = json.loads(d["payload_json"])
            except (json.JSONDecodeError, TypeError):
                d["payload_json"] = {}
            result.append(d)
        return result

    def mark_turn_settled(self, session_id: str, turn_count: int) -> None:
        now = _now()
        self._conn.execute(
            "UPDATE sessions SET turn_count = ?, updated_at = ? WHERE session_id = ?",
            (turn_count, now, session_id),
        )
        self._conn.commit()

    def mark_session_closed(self, session_id: str) -> None:
        now = _now()
        self._conn.execute(
            "UPDATE sessions SET status = 'closed', updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        self._conn.commit()
