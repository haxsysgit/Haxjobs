"""Activity log."""
from .schema import get_db


def _log(event_type, message, detail="", job_id=None):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (event_type, message, detail, job_id) VALUES (?, ?, ?, ?)",
                 (event_type, message, detail, job_id))
    conn.commit()
    conn.close()


def get_recent_activity(limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
        (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
