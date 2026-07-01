"""Decisions request/response schemas."""
from pydantic import BaseModel


class DecisionRequest(BaseModel):
    job_id: int
    decision: str  # apply, skip, reject
    notes: str | None = None
