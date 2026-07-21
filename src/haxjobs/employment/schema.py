"""Career graph schema — Pydantic models for the relational career data layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr, field_validator


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


Proficiency = Literal["primary", "strong", "working", "learning"]
PrivacyLevel = Literal["public_ok", "private"]
PreferenceWeight = Literal["strong", "weak"]


class Person(BaseModel):
    person_id: str
    name: str
    location: str
    work_authorization: str = ""
    notice_period: str = ""
    salary_range: str = ""
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class CareerTrack(BaseModel):
    track_id: str
    person_id: str
    name: str
    target_role_families: list[str] = Field(default_factory=list)
    excluded_role_families: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class Skill(BaseModel):
    skill_id: str
    track_id: str
    name: str
    parent_skill_id: str | None = None
    proficiency: Proficiency
    created_at: str = Field(default_factory=_utcnow)

    @field_validator("parent_skill_id")
    @classmethod
    def parent_must_be_null_or_non_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


class EvidenceItem(BaseModel):
    evidence_id: str
    label: str
    source: str
    content: str
    verified_at: str | None = None
    privacy_level: PrivacyLevel = "public_ok"
    created_at: str = Field(default_factory=_utcnow)

    @field_validator("verified_at")
    @classmethod
    def verified_at_must_be_valid_iso(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Validate ISO 8601 parseable
        try:
            from datetime import datetime
            datetime.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError(f"verified_at must be valid ISO 8601, got: {v}")
        return v


class SkillEvidence(BaseModel):
    skill_id: str
    evidence_id: str


class SkillGap(BaseModel):
    gap_id: str
    track_id: str
    skill_name: str
    target_proficiency: Proficiency
    note: str = ""
    created_at: str = Field(default_factory=_utcnow)


class HardConstraint(BaseModel):
    constraint_id: str
    track_id: str
    constraint_text: str
    created_at: str = Field(default_factory=_utcnow)


class Preference(BaseModel):
    preference_id: str
    track_id: str
    key: str
    value: str
    weight: PreferenceWeight = "strong"
    created_at: str = Field(default_factory=_utcnow)


# ── Plan 004: Job and Assessment models ──

class Job(BaseModel):
    """A normalized saved job."""
    job_id: str
    external_ref: str
    employer_name: str | None = None
    title: str
    location: str
    source_url: str
    source_type: str
    description: str
    source_status: str = ""
    description_kind: str = ""
    description_complete: bool = False
    observed_at: str
    allowed_source_hosts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_content_hash: str = ""
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class ConstraintCheck(BaseModel):
    constraint_id: str
    constraint_text: str
    result: Literal["pass", "fail", "unknown"]


class JobAssessment(BaseModel):
    assessment_id: str = ""  # stable ID derived from tool_call_id; store-populated
    _replayed: bool = PrivateAttr(default=False)
    job_id: str
    track_id: str
    tool_call_id: str
    recommendation: Literal["pursue", "consider", "skip", "needs_more_information"]
    summary: str
    constraint_checks: list[ConstraintCheck] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_content_hash: str = ""
    sequence: int | None = None  # store-populated output-only
    created_at: str = Field(default_factory=_utcnow)

    @property
    def replayed(self) -> bool:
        """Whether this result came from an idempotent existing write."""
        return self._replayed
