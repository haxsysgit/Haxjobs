"""Decisions CRUD."""
from .schema import get_db
from .activity import _log


def record_decision(job_id, decision, reason=""):
    conn = get_db()
    conn.execute("INSERT INTO decisions (job_id, decision, reason) VALUES (?, ?, ?)",
                 (job_id, decision, reason))
    conn.commit()
    conn.close()
    _log("user_decision", f"{decision} — {reason[:60]}", job_id=job_id)


def get_decisions(job_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM decisions WHERE job_id=? ORDER BY decided_at DESC",
        (job_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
