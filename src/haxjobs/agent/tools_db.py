"""Read-only database query tool (admin/support only)."""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from haxjobs.agent.registry import register
from haxjobs.db.schema import get_db

MAX_DB_ROWS = 50


def _first_token(sql: str) -> str:
    cleaned = re.sub(r"(?s)/\*.*?\*/", " ", sql).strip()
    cleaned = re.sub(r"(?m)^\s*--.*$", " ", cleaned).strip()
    return (cleaned.split(None, 1)[0] if cleaned else "").lower()


def _readonly_authorizer(action, _arg1, _arg2, _db, _trigger):
    denied = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_PRAGMA,
    }
    return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK


def db_query(sql: str) -> dict[str, Any]:
    """Run a read-only SQLite query against the HaxJobs DB."""
    if _first_token(sql) not in {"select", "with"}:
        return {"error": "db_query only accepts SELECT or WITH queries"}

    conn = get_db()
    conn.set_authorizer(_readonly_authorizer)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_DB_ROWS + 1)
        truncated = len(rows) > MAX_DB_ROWS
        rows = rows[:MAX_DB_ROWS]
        return {
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }
    except Exception as e:
        return {"error": f"db_query failed: {e}"}
    finally:
        conn.close()


register(
    "db_query",
    {
        "name": "db_query",
        "description": "Run a read-only SELECT/WITH query against the HaxJobs SQLite database.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "Read-only SQL query"},
            },
            "required": ["sql"],
        },
    },
    db_query,
)
