"""Discovered (pre-promotion) job CRUD operations.

Every job enters HaxJobs through this layer — scrapers, manual entry, and
email intake all normalize into this table first. Dedup, blacklist, and filter
hooks run before promotion to the main ``jobs`` table.
"""
import json
import sqlite3
from .schema import get_db


def insert_discovered_job(record: dict) -> int | None:
    """Insert a raw discovered job and return its row id, or None on duplicate."""
    conn = get_db()

    # Check for existing duplicate first. Keep the original row's status intact:
    # it may still be the accepted/new row that should be promoted.
    if _find_duplicate_inner(conn, record):
        conn.close()
        return None

    cur = conn.execute("""
        INSERT INTO discovered_jobs (
            source, source_url, apply_url, ats, external_id,
            title, company, location, jd_text, raw_payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.get("source", "manual"),
        record.get("source_url", ""),
        record.get("apply_url", ""),
        record.get("ats", ""),
        record.get("external_id", ""),
        record.get("title", ""),
        record.get("company", ""),
        record.get("location", ""),
        record.get("jd_text", ""),
        json.dumps(record.get("raw_payload", {})),
    ))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def _find_duplicate_inner(conn, record: dict) -> dict | None:
    """Check if a record duplicates an existing discovered job.

    Returns the existing row dict if found, else None.
    Matches on:
    1. ``source_url`` (exact, non-empty)
    2. ``company`` + ``title`` (case-insensitive)
    """
    source_url = (record.get("source_url") or "").strip()
    company = (record.get("company") or "").strip()
    title = (record.get("title") or "").strip()

    if source_url:
        row = conn.execute(
            "SELECT * FROM discovered_jobs WHERE source_url=?",
            (source_url,),
        ).fetchone()
        if row:
            return dict(row)

    if company and title:
        row = conn.execute(
            "SELECT * FROM discovered_jobs "
            "WHERE LOWER(company)=LOWER(?) AND LOWER(title)=LOWER(?)",
            (company, title),
        ).fetchone()
        if row:
            return dict(row)

    return None


def find_duplicate(record: dict) -> dict | None:
    """Public wrapper — check if a record duplicates an existing discovered job."""
    conn = get_db()
    result = _find_duplicate_inner(conn, record)
    conn.close()
    return result


def list_discovered_jobs(status: str | None = None, limit: int = 100) -> list[dict]:
    """List discovered jobs, optionally filtered by status."""
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM discovered_jobs WHERE discovery_status=? "
            "ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM discovered_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_discovered_job(discovered_id: int) -> dict | None:
    """Get a single discovered job by id."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM discovered_jobs WHERE id=?", (discovered_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _find_existing_job_id(discovered: dict) -> int | None:
    conn = get_db()
    row = None
    external_id = (discovered.get("external_id") or "").strip()
    source_url = (discovered.get("source_url") or "").strip()
    if external_id:
        row = conn.execute("SELECT id FROM jobs WHERE external_id=?", (external_id,)).fetchone()
    if row is None and source_url:
        row = conn.execute("SELECT id FROM jobs WHERE source_url=?", (source_url,)).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def update_discovery_status(discovered_id: int, status: str, reason: str = "") -> None:
    """Update the discovery_status (and optionally filter_reason) of a discovered job."""
    conn = get_db()
    if reason:
        conn.execute(
            "UPDATE discovered_jobs SET discovery_status=?, filter_reason=?, "
            "updated_at=datetime('now') WHERE id=?",
            (status, reason, discovered_id),
        )
    else:
        conn.execute(
            "UPDATE discovered_jobs SET discovery_status=?, "
            "updated_at=datetime('now') WHERE id=?",
            (status, discovered_id),
        )
    conn.commit()
    conn.close()


def promote_discovered_job(discovered_id: int) -> int | None:
    """Promote a discovered job into the main ``jobs`` table.

    Returns the ``jobs.id``, or None if the discovered job is not eligible.
    """
    from .jobs import insert_job

    discovered = get_discovered_job(discovered_id)
    if not discovered:
        return None
    if discovered["discovery_status"] not in ("new", "accepted"):
        return None

    existing_job_id = _find_existing_job_id(discovered)
    job_id = existing_job_id or insert_job(
        discovered["title"],
        discovered["company"],
        location=discovered["location"],
        jd_text=discovered["jd_text"],
        source_url=discovered["source_url"],
        source=discovered["source"],
        external_id=discovered["external_id"] or None,
    )
    if job_id is None:
        job_id = _find_existing_job_id(discovered)
    if job_id is None:
        return None

    conn = get_db()
    conn.execute(
        "UPDATE discovered_jobs SET discovery_status='promoted', "
        "promoted_job_id=?, updated_at=datetime('now') WHERE id=?",
        (job_id, discovered_id),
    )
    conn.commit()
    conn.close()

    from .activity import _log
    _log("discovery_promoted",
         f"Discovered job #{discovered_id} promoted to jobs #{job_id}",
         job_id=job_id)
    return job_id
