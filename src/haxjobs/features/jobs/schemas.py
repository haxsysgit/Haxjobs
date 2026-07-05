"""Job request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JobListItem(BaseModel):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    source_url: str | None = None
    jd_text: str | None = None
    status: str = "pending"
    source: str | None = None
    discovered_at: str | None = None
    role_family: str | None = None
    recommended_cv_variant: str | None = None
    pack_status: str | None = None
    pack_dir: str | None = None
    fit_score: int | None = None
    fit_level: int | None = None
    fit_verdict: str | None = None
    level: int | None = None
    level_name: str | None = None
    summary: str | None = None
    strongest_matches: list[str] | None = None
    major_gaps: list[str] | None = None
    sponsorship_risk: str | None = None
    evaluated_at: str | None = None


class JobDetail(JobListItem):
    evaluation: dict[str, Any] | None = None
    decisions: list[dict[str, Any]] = []


class JobsListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int
