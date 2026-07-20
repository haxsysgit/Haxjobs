"""Pydantic contracts for machine job fixtures and career fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    """One labelled piece of career evidence with provenance."""

    label: str
    source: str
    content: str

    @field_validator("source")
    @classmethod
    def source_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("evidence source must not be empty")
        return v


class CareerFixture(BaseModel):
    """Frozen career fixture — direction, constraints, and evidence."""

    fixture_id: str
    fixture_version: int
    career_direction: str
    hard_constraints: list[str]
    evidence: list[EvidenceItem]
    preferred_locations: list[str] = Field(default_factory=list)
    target_role_families: list[str] = Field(default_factory=list)
    excluded_role_families: list[str] = Field(default_factory=list)
    work_authorization: str = ""

    @field_validator("evidence")
    @classmethod
    def at_least_one_evidence_item(cls, v: list[EvidenceItem]) -> list[EvidenceItem]:
        if not v:
            raise ValueError("career fixture must have at least one evidence item")
        return v


class JobFixture(BaseModel):
    """Machine-readable job fixture — source-limited evidence only."""

    fixture_id: str
    fixture_version: int
    job_ref: int
    observed_at: str
    source_type: str
    source_url: str
    source_status: str
    allowed_source_hosts: list[str] = Field(default_factory=list)
    title: str
    employer_name: str | None
    location: str
    description: str
    description_kind: str
    content_complete: bool
    warnings: list[str] = Field(default_factory=list)

    @field_validator("observed_at")
    @classmethod
    def must_have_observation_date(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("job fixture must have observation date")
        return v

    @field_validator("employer_name", mode="before")
    @classmethod
    def null_employer_ok(cls, v: Any) -> Any:
        return v  # None is acceptable for stub fixtures


def load_career_fixture(path: str | Path) -> CareerFixture:
    """Load and validate a career fixture from a JSON file."""
    raw = json.loads(Path(path).read_text())
    return CareerFixture.model_validate(raw)


def load_job_fixture(path: str | Path) -> JobFixture:
    """Load and validate a job fixture from a JSON file."""
    raw = json.loads(Path(path).read_text())
    return JobFixture.model_validate(raw)
