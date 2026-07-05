"""Decisions business logic."""
from haxjobs import product_tools
from haxjobs.db.schema import get_db


def get_decisions(job_id: int | None = None):
    """Return decisions, optionally filtered by job_id. Includes job_title and job_company for feed display."""
    from haxjobs.db.decisions import get_decisions as _db_get
    if job_id:
        return _db_get(job_id)
    # Recent decisions across all jobs, with title/company for feed display
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT d.*, j.title as job_title, j.company as job_company
               FROM decisions d
               LEFT JOIN jobs j ON d.job_id = j.id
               ORDER BY d.decided_at DESC LIMIT 50"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def record_decision(job_id: int, decision: str, reason: str = ""):
    """Record a user decision via the shared product tool."""
    return product_tools.record_decision(job_id, decision, reason=reason)
