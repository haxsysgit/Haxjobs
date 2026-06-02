from pydantic import BaseModel, ConfigDict


class UserProfileCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    work_authorization_summary: str | None = None
    requires_sponsorship: str | None = None
    salary_preference: str | None = None
    availability: str | None = None
    preferred_locations: list[str] = []
    preferred_work_modes: list[str] = []
    preferred_roles: list[str] = []


class UserProfileRead(UserProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str


class ProfileFactCreate(BaseModel):
    category: str
    claim: str
    safe_wording: str | None = None
    avoid_wording: str | None = None
    evidence_source: str | None = None
    confidence: str = "needs_confirmation"


class ProfileFactRead(ProfileFactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str


class SavedAnswerCreate(BaseModel):
    question_key: str
    question_text: str
    answer: str | None = None
    sensitivity: str = "review_before_use"


class SavedAnswerRead(SavedAnswerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
