"""Onboarding request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


# ── profile field definitions ──

REQUIRED_FIELDS = {
    "user_profile.name": {
        "question": "What is your full name?",
        "type": "text",
        "description": "Your legal name as it should appear on applications",
    },
    "user_profile.email": {
        "question": "What is your email address?",
        "type": "text",
        "description": "Primary contact email for job applications",
    },
    "user_profile.location": {
        "question": "Where are you based? (city, country)",
        "type": "text",
        "description": "Current city and country for location filtering",
    },
    "user_profile.work_authorization_summary": {
        "question": "What is your work authorization status? (e.g. citizen, visa type, need sponsorship)",
        "type": "text",
        "description": "Used to assess sponsorship risk for each job",
    },
    "preferred_roles": {
        "question": "What roles are you targeting? (comma-separated, e.g. Backend Engineer, Full Stack, AI Engineer)",
        "type": "list",
        "description": "Job titles you want — used for discovery and matching",
    },
    "preferred_locations": {
        "question": "What locations will you work in? (comma-separated, e.g. London, Remote UK, Manchester)",
        "type": "list",
        "description": "Cities or regions — jobs outside these are filtered out",
    },
    "preferred_work_modes": {
        "question": "What work modes do you prefer? (comma-separated: remote, hybrid, onsite)",
        "type": "list",
        "description": "Used to filter by workplace arrangement",
    },
}

# Fields the agent should try to infer from CV text.
# If found during extraction, we skip the question.
AGENT_INFERRED_FIELDS = {
    "user_profile.name",
    "user_profile.email",
    "user_profile.phone",
    "user_profile.location",
    "skills",
}


# ── API models ──


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
    phase: str = "required"  # "required" | "deep" | "complete"


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
