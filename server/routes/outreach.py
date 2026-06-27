"""Outreach API routes for the HaxJobs dashboard and Telegram integration.

GET  /api/outreach/jobs     → Jobs with drafts and connected pack info
GET  /api/outreach/drafts   → All drafts with job + contact details
POST /api/outreach/approve  → Approve a draft by ID
POST /api/outreach/reject   → Reject a draft with optional reason
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from db import schema
from db.outreach import (
    get_drafts,
    update_draft_status,
)

def _get_db():
    return schema.get_db()


def list_outreach_jobs() -> list[dict[str, Any]]:
    """Get jobs that have outreach drafts, with pack and fit info."""
    schema.init()
    conn = _get_db()

    rows = conn.execute("""
        SELECT DISTINCT j.id, j.title, j.company, j.location, j.source_url,
               j.outreach_status, j.pack_status, j.pack_dir,
               e.fit_score, e.fit_verdict, e.level_name, e.summary,
               j.role_family, j.recommended_cv_variant,
               (SELECT count(*) FROM outreach_drafts d WHERE d.job_id = j.id AND d.status = 'draft') as draft_count,
               (SELECT count(*) FROM outreach_drafts d WHERE d.job_id = j.id AND d.status = 'approved') as approved_count,
               (SELECT count(*) FROM outreach_drafts d WHERE d.job_id = j.id AND d.status = 'sent') as sent_count,
               (SELECT count(*) FROM outreach_contacts c WHERE c.job_id = j.id) as contact_count
        FROM jobs j
        JOIN evaluations e ON j.id = e.job_id
        WHERE j.id IN (SELECT DISTINCT job_id FROM outreach_drafts)
        ORDER BY e.fit_score DESC
        LIMIT 50
    """).fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "title": r["title"],
            "company": r["company"],
            "location": r["location"] or "",
            "sourceUrl": r["source_url"] or "",
            "fitScore": r["fit_score"] or 0,
            "fitVerdict": r["fit_verdict"] or "",
            "levelName": r["level_name"] or "",
            "summary": r["summary"] or "",
            "outreachStatus": r["outreach_status"] or "none",
            "packStatus": r["pack_status"] or "none",
            "packDir": r["pack_dir"] or "",
            "roleFamily": r["role_family"] or "",
            "recommendedCvVariant": r["recommended_cv_variant"] or "",
            "draftCount": r["draft_count"],
            "approvedCount": r["approved_count"],
            "sentCount": r["sent_count"],
            "contactCount": r["contact_count"],
        })

    conn.close()
    return result


def list_outreach_drafts(job_id: int | None = None) -> list[dict[str, Any]]:
    """Get outreach drafts, optionally filtered by job."""
    schema.init()
    conn = _get_db()

    if job_id:
        rows = conn.execute("""
            SELECT d.*, j.title as job_title, j.company as job_company,
                   j.outreach_status, j.pack_status, j.pack_dir,
                   e.fit_score, e.fit_verdict,
                   c.name as contact_name, c.title as contact_title
            FROM outreach_drafts d
            JOIN jobs j ON d.job_id = j.id
            LEFT JOIN evaluations e ON j.id = e.job_id
            LEFT JOIN outreach_contacts c ON d.contact_id = c.id
            WHERE d.job_id = ?
            ORDER BY d.created_at DESC
        """, (job_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT d.*, j.title as job_title, j.company as job_company,
                   j.outreach_status, j.pack_status, j.pack_dir,
                   e.fit_score, e.fit_verdict,
                   c.name as contact_name, c.title as contact_title
            FROM outreach_drafts d
            JOIN jobs j ON d.job_id = j.id
            LEFT JOIN evaluations e ON j.id = e.job_id
            LEFT JOIN outreach_contacts c ON d.contact_id = c.id
            ORDER BY d.created_at DESC
            LIMIT 100
        """).fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "jobId": r["job_id"],
            "contactId": r["contact_id"],
            "subject": r["subject"],
            "messageText": r["message_text"],
            "status": r["status"],
            "sentAt": r["sent_at"],
            "createdAt": r["created_at"],
            "jobTitle": r["job_title"],
            "jobCompany": r["job_company"],
            "outreachStatus": r["outreach_status"] or "",
            "packStatus": r["pack_status"] or "",
            "packDir": r["pack_dir"] or "",
            "fitScore": r["fit_score"] or 0,
            "fitVerdict": r["fit_verdict"] or "",
            "contactName": r["contact_name"] or "",
            "contactTitle": r["contact_title"] or "",
        })

    conn.close()
    return result


def approve_draft(draft_id: int) -> dict[str, Any]:
    """Approve a draft message. Returns ok: false if draft not found."""
    schema.init()
    try:
        updated = update_draft_status(draft_id, "approved")
        if not updated:
            return {"ok": False, "error": "draft not found", "draft_id": draft_id}
        return {"ok": True, "draft_id": draft_id, "status": "approved"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reject_draft(draft_id: int, reason: str = "") -> dict[str, Any]:
    """Reject a draft message. Returns ok: false if draft not found."""
    schema.init()
    try:
        updated = update_draft_status(draft_id, "rejected")
        if not updated:
            return {"ok": False, "error": "draft not found", "draft_id": draft_id}
        return {"ok": True, "draft_id": draft_id, "status": "rejected", "reason": reason}
    except Exception as e:
        return {"ok": False, "error": str(e)}
