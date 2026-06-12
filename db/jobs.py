"""Job CRUD operations."""
import json
import sqlite3
from .schema import get_db
from .activity import _log
from .role_classification import classify_job_payload


def insert_job(title, company, location="", jd_text="", source_url="", source="unknown",
               external_id=None):
    conn = get_db()
    if external_id:
        existing = conn.execute("SELECT id FROM jobs WHERE external_id=?", (external_id,)).fetchone()
        if existing:
            conn.close()
            return None
    classification = classify_job_payload(title=title, jd_text=jd_text, source=source)
    cur = conn.execute("""
        INSERT INTO jobs (
            external_id, title, company, location, jd_text, source_url, source,
            source_quality, role_family, role_family_confidence,
            recommended_cv_variant, role_family_terms
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        external_id, title, company, location, jd_text, source_url, source,
        classification["source_quality"],
        classification["role_family"],
        classification["role_family_confidence"],
        classification["recommended_cv_variant"],
        classification["role_family_terms"],
    ))
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    _log("job_discovered", f"{title[:60]} at {company}", job_id=job_id)
    return job_id


def get_pending_jobs(limit=None):
    conn = get_db()
    query = "SELECT * FROM jobs WHERE status='pending' ORDER BY discovered_at ASC"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job(job_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_jobs(status_filter=None):
    conn = get_db()
    if status_filter:
        rows = conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY discovered_at DESC",
                           (status_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY discovered_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(job_id, status):
    conn = get_db()
    conn.execute("UPDATE jobs SET status=?, updated_at=datetime('now') WHERE id=?",
                 (status, job_id))
    conn.commit()
    conn.close()


def update_job_pack_status(job_id, pack_status):
    conn = get_db()
    conn.execute("UPDATE jobs SET pack_status=?, updated_at=datetime('now') WHERE id=?",
                 (pack_status, job_id))
    conn.commit()
    conn.close()


def job_count_by_status():
    conn = get_db()
    rows = conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}
