"""Onboarding request/response schemas."""
from pydantic import BaseModel


class OnboardingStatusResponse(BaseModel):
    stage: str = "not_started"
    message: str = "Onboarding not yet implemented"
