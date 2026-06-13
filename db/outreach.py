"""Outreach database helpers — contacts and draft messages."""

from __future__ import annotations

import sqlite3
from .schema import get_db, init

def ensure_outreach_tables():
    """Create outreach tables if needed (schema.init also does this)."""
    # Add specific outreach-related indexes if needed
    conn = get_db()
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_contacts_job_company "
        "ON outreach_contacts(job_id, company)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_drafts_job_status "
        "ON outreach_drafts(job_id, status)"
    )
    conn.commit()
    conn.close()


def insert_contact(
    job_id: int,
    name: str,
    title: str,
    company: str,
    linkedin_url: str = "",
    github_url: str = "",
    found_via: str = "linkedin",
    relevance: str = "medium",
) -> int | None:
    """Insert an outreach contact. Returns id or None if duplicate."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM outreach_contacts WHERE job_id=? AND linkedin_url=? AND linkedin_url!=''",
        (job_id, linkedin_url),
    ).fetchone()
    if existing:
        conn.close()
        return None

    cur = conn.execute(
        """INSERT INTO outreach_contacts
           (job_id, name, title, company, linkedin_url, github_url, found_via, relevance)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, name, title, company, linkedin_url, github_url, found_via, relevance),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def insert_draft(
    job_id: int,
    subject: str,
    message_text: str,
    contact_id: int | None = None,
    status: str = "draft",
) -> int:
    """Insert a draft outreach message. Returns id."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO outreach_drafts (job_id, contact_id, subject, message_text, status)
           VALUES (?, ?, ?, ?, ?)""",
        (job_id, contact_id, subject, message_text, status),
    )
    conn.commit()
    did = cur.lastrowid
    conn.close()
    return did


def get_jobs_for_outreach(min_score: int = 75) -> list[dict]:
    """Get high-fit jobs that haven't been contacted yet."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT j.id, j.title, j.company, j.location, j.source_url,
                  e.fit_score, e.fit_verdict, e.strongest_matches, e.major_gaps,
                  e.summary, j.outreach_status
           FROM jobs j
           JOIN evaluations e ON j.id = e.job_id
           WHERE e.fit_score >= ?
             AND j.outreach_status IN ('none', '')
           ORDER BY e.fit_score DESC
           LIMIT 30""",
        (min_score,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_drafts(status: str | None = None) -> list[dict]:
    """Get outreach drafts, optionally filtered by status."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            """SELECT d.*, j.title as job_title, j.company as job_company,
                      c.name as contact_name, c.title as contact_title
               FROM outreach_drafts d
               JOIN jobs j ON d.job_id = j.id
               LEFT JOIN outreach_contacts c ON d.contact_id = c.id
               WHERE d.status = ?
               ORDER BY d.created_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT d.*, j.title as job_title, j.company as job_company,
                      c.name as contact_name, c.title as contact_title
               FROM outreach_drafts d
               JOIN jobs j ON d.job_id = j.id
               LEFT JOIN outreach_contacts c ON d.contact_id = c.id
               ORDER BY d.created_at DESC
               LIMIT 50"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_draft_status(draft_id: int, status: str):
    """Update a draft's status (draft, approved, sent)."""
    conn = get_db()
    if status == "sent":
        conn.execute(
            "UPDATE outreach_drafts SET status=?, sent_at=datetime('now') WHERE id=?",
            (status, draft_id),
        )
    else:
        conn.execute(
            "UPDATE outreach_drafts SET status=? WHERE id=?", (status, draft_id)
        )
    conn.commit()
    conn.close()


def get_contacts_for_job(job_id: int) -> list[dict]:
    """Get all contacts found for a specific job."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM outreach_contacts WHERE job_id=? ORDER BY relevance, created_at DESC",
        (job_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_job_outreach_status(job_id: int, status: str):
    """Update the outreach_status on the jobs table."""
    conn = get_db()
    conn.execute(
        "UPDATE jobs SET outreach_status=?, updated_at=datetime('now') WHERE id=?",
        (status, job_id),
    )
    conn.commit()
    conn.close()
