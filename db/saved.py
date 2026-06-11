"""Saved jobs CRUD."""
import sqlite3
from .schema import get_db
from .activity import _log


def save_job(job_id, notes=""):
    conn = get_db()
    try:
        conn.execute("INSERT INTO saved_jobs (job_id, notes) VALUES (?, ?)",
                    (job_id, notes))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    _log("job_saved", f"Job {job_id}", job_id=job_id)
    return ok


def unsave_job(job_id):
    conn = get_db()
    conn.execute("DELETE FROM saved_jobs WHERE job_id=?", (job_id,))
    conn.commit()
    conn.close()


def get_saved_jobs():
    conn = get_db()
    rows = conn.execute("""
        SELECT j.*, s.notes as saved_notes, s.created_at as saved_at
        FROM saved_jobs s
        JOIN jobs j ON j.id = s.job_id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
