"""Decisions request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing_extensions import Literal


class DecisionRequest(BaseModel):
    job_id: int
    decision: Literal["apply", "maybe", "save", "skip", "reject"]
    reason: str = ""


class DecisionResponse(BaseModel):
    ok: bool
    job_id: int | None = None
    decision: str | None = None
    decision_id: int | None = None
    code: str | None = None
    error: str | None = None
