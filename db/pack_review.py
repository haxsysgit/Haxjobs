"""Pack review lifecycle helpers.

Generated packs stay gated until Arinze explicitly approves, rejects, or asks
for changes. This module keeps that state on the job row and mirrors the action
into the decisions table for audit history.
"""

from __future__ import annotations

from typing import Any

from .decisions import record_decision
from .schema import get_db


REVIEW_ACTIONS = {
    "approve": ("reviewed_approved", "approved", "pack_review_approved"),
    "reject": ("reviewed_rejected", "rejected", "pack_review_rejected"),
    "changes": (
        "review_changes_requested",
        "changes_requested",
        "pack_review_changes_requested",
    ),
}


def review_pack(job_id: int, action: str, notes: str = "") -> dict[str, Any]:
    """Record a manual review decision for a generated application pack.

    Only allows review on packs with a reviewable status:
    'generated' or 'review_changes_requested'.
    """
    if action not in REVIEW_ACTIONS:
        return {
            "ok": False,
            "error": f"Invalid review action: {action}",
            "valid_actions": sorted(REVIEW_ACTIONS),
        }

    pack_status, review_status, decision = REVIEW_ACTIONS[action]
    conn = get_db()
    row = conn.execute(
        "SELECT id, pack_status FROM jobs WHERE id=?", (job_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return {"ok": False, "error": "job not found"}

    current_pack_status = row["pack_status"] or "none"

    # Only allow review when a pack is generated or changes were requested
    if current_pack_status not in ("generated", "review_changes_requested"):
        conn.close()
        return {
            "ok": False,
            "error": f"no pack to review (current status: {current_pack_status})",
            "current_pack_status": current_pack_status,
        }

    conn.execute(
        """
        UPDATE jobs
        SET pack_status=?, pack_review_status=?, pack_review_notes=?,
            pack_reviewed_at=datetime('now'), updated_at=datetime('now')
        WHERE id=?
        """,
        (pack_status, review_status, notes, job_id),
    )
    conn.commit()
    conn.close()
    record_decision(job_id, decision, notes)

    return {
        "ok": True,
        "job_id": job_id,
        "pack_status": pack_status,
        "pack_review_status": review_status,
        "review_notes": notes,
    }


def get_pack_review(job_id: int) -> dict[str, Any] | None:
    """Return the current pack review fields for a job."""
    conn = get_db()
    row = conn.execute(
        """
        SELECT pack_review_status, pack_review_notes, pack_reviewed_at
        FROM jobs
        WHERE id=?
        """,
        (job_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "pack_review_status": row["pack_review_status"],
        "review_notes": row["pack_review_notes"],
        "reviewed_at": row["pack_reviewed_at"],
    }
