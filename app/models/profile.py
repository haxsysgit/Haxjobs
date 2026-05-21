from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocumentKind = Literal["cv", "jd"]


class ProfileDocument(BaseModel):
    id: str
    label: str
    kind: DocumentKind
    added_at: str
    summary: str
    skills: list[str] = Field(default_factory=list)
    text: str | None = Field(default=None, exclude=True)


class ProfileFact(BaseModel):
    id: str
    category: str
    text: str
    source_label: str


class ProfileJobRecord(BaseModel):
    id: str
    role_title: str
    jd_label: str
    mode: str
    fit_score: int
    matched_requirements: int
    total_requirements: int
    added_at: str
    focus_skills: list[str] = Field(default_factory=list)


class ProfileSurveyResponse(BaseModel):
    question_key: str
    job_id: str
    requirement_id: str
    requirement_text: str
    choice_id: str
    choice_label: str
    notes: str = ""
    updated_at: str


class CandidateProfile(BaseModel):
    version: str = "0.3.0"
    created_at: str
    updated_at: str
    summary: str
    top_skills: list[str] = Field(default_factory=list)
    cv_documents: list[ProfileDocument] = Field(default_factory=list)
    jd_history: list[ProfileJobRecord] = Field(default_factory=list)
    evidence_library: list[ProfileFact] = Field(default_factory=list)
    survey_responses: list[ProfileSurveyResponse] = Field(default_factory=list)


class ProfileExportBundle(BaseModel):
    profile: CandidateProfile
    documents: dict[str, str] = Field(default_factory=dict)


class SaveSurveyResponseRequest(BaseModel):
    job_id: str
    requirement_id: str
    requirement_text: str
    choice_id: str
    choice_label: str
    notes: str = ""
