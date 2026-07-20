"""Career graph schema — Pydantic models for the relational career data layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
