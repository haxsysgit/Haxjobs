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

    # Check for existing duplicate first
    dup = _find_duplicate_inner(conn, record)
    if dup:
        # Mark the existing one as duplicate if it was 'new'
        if dup["discovery_status"] == "new":
            conn.execute(
                "UPDATE discovered_jobs SET discovery_status='duplicate', "
                "filter_reason='duplicate source_url or company+title', "
                "updated_at=datetime('now') WHERE id=?",
                (dup["id"],),
            )
            conn.commit()
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

    Returns the new ``jobs.id``, or None if the discovered job is not eligible.
    """
    from .jobs import insert_job

    discovered = get_discovered_job(discovered_id)
    if not discovered:
        return None
    if discovered["discovery_status"] not in ("new", "accepted"):
        return None

    conn = get_db()
    cur = conn.execute("""
        INSERT OR IGNORE INTO jobs (
            external_id, title, company, location, jd_text,
            source_url, source, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (
        discovered["external_id"] or None,
        discovered["title"],
        discovered["company"],
        discovered["location"],
        discovered["jd_text"],
        discovered["source_url"],
        discovered["source"],
    ))
    conn.commit()
    job_id = cur.lastrowid

    if job_id is None:
        # Job already existed (external_id collision in main table)
        conn.close()
        return None

    # Mark discovered job as promoted
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
