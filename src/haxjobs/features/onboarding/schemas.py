"""Onboarding request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class CVUploadResponse(BaseModel):
    profile: dict
    next_question: dict | None = None
    stage: str = "extraction_done"


class WizardAnswer(BaseModel):
    question_id: str   # dot-path to profile field, e.g. "user_profile.phone"
    answer: str


class WizardResponse(BaseModel):
    profile: dict
    next_question: dict | None = None  # None = wizard complete
    stage: str


class OnboardingStatusResponse(BaseModel):
    stage: str   # "not_started" | "extraction_done" | "wizard_in_progress" | "complete"
    has_profile: bool
