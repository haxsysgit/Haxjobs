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
        "SELECT * FROM decisions WHERE job_id=? ORDER BY id DESC",
        (job_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_auto_apply_states(job_ids):
    """Return {job_id: bool} for the latest auto-apply decision per job.

    Only considers 'auto_apply' and 'auto_apply_remove' decisions.
    Latest by MAX(id) wins (not timestamp, since SQLite timestamps can tie).
    Jobs with no auto-apply decisions are omitted (caller should default to False).
    """
    if not job_ids:
        return {}

    conn = get_db()
    placeholders = ",".join("?" * len(job_ids))
    # Find the latest (max id) auto-apply or auto-apply-remove decision per job
    rows = conn.execute(f"""
        SELECT d.job_id, d.decision
        FROM decisions d
        INNER JOIN (
            SELECT job_id, MAX(id) AS max_id
            FROM decisions
            WHERE job_id IN ({placeholders})
              AND decision IN ('auto_apply', 'auto_apply_remove')
            GROUP BY job_id
        ) latest
        ON d.job_id = latest.job_id AND d.id = latest.max_id
    """, tuple(job_ids)).fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row["job_id"]] = row["decision"] == "auto_apply"
    return result
