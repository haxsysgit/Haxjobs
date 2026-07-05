"""Decisions business logic."""
from haxjobs import product_tools


def get_decisions(job_id: int | None = None):
    """Return decisions, optionally filtered by job_id."""
    from haxjobs.db.decisions import get_decisions as _db_get
    if job_id:
        return _db_get(job_id)
    return []


def record_decision(job_id: int, decision: str, notes: str | None = None):
    """Record a user decision via the shared product tool."""
    return product_tools.record_decision(job_id, decision, reason=notes or "")
