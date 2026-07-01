"""Decisions business logic.

ponytail: placeholder. Real logic in plan 051.
"""

def get_decisions():
    return []


def record_decision(job_id: int, decision: str, notes: str | None = None):
    return {"job_id": job_id, "decision": decision, "notes": notes, "status": "not_implemented"}
