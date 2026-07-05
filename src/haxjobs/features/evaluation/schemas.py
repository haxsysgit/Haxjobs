"""Evaluation request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvaluationRunRequest(BaseModel):
    auto_generate_pack: bool = True


class EvaluationRunResponse(BaseModel):
    ok: bool
    job_id: int | None = None
    fit_score: int | None = None
    level: int | None = None
    level_name: str | None = None
    fit_verdict: str | None = None
    strongest_matches: list[str] | None = None
    major_gaps: list[str] | None = None
    sponsorship_risk: str | None = None
    summary: str | None = None
    pack: dict[str, Any] | None = None
    code: str | None = None
    error: str | None = None
