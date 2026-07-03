"""Onboarding request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class FieldQuestion(BaseModel):
    field: str
    question: str
    type: str  # "text" | "list"
    description: str
    current_value: str | list[str] | None = None


class CVUploadResponse(BaseModel):
    profile: dict
    next_question: FieldQuestion | None = None
    questions_remaining: int = 0
    phase: str = "wizard"


class WizardAnswer(BaseModel):
    question_id: str
    answer: str


class WizardResponse(BaseModel):
    profile: dict
    next_question: FieldQuestion | None = None
    questions_remaining: int = 0
    phase: str


class OnboardingStatusResponse(BaseModel):
    stage: str
    has_profile: bool
