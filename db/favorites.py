"""Favorites CRUD."""
import sqlite3
from .schema import get_db
from .activity import _log


def add_favorite(job_id):
    conn = get_db()
    try:
        conn.execute("INSERT INTO favorites (job_id) VALUES (?)", (job_id,))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    _log("favorite_added", f"Job {job_id}", job_id=job_id)
    return ok


def remove_favorite(job_id):
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE job_id=?", (job_id,))
    conn.commit()
    conn.close()
    _log("favorite_removed", f"Job {job_id}", job_id=job_id)


def get_favorites():
    conn = get_db()
    rows = conn.execute("SELECT job_id FROM favorites ORDER BY created_at DESC").fetchall()
    conn.close()
    return [r["job_id"] for r in rows]


def is_favorite(job_id):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM favorites WHERE job_id=?", (job_id,)).fetchone()
    conn.close()
    return row is not None
