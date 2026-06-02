from pydantic import BaseModel, ConfigDict


class ApplicationCreate(BaseModel):
    job_id: str
    status: str = "Saved"
    fit_score: int | None = None
    sponsorship_risk: str | None = None
    recommendation: str | None = None
    next_action: str | None = None
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    fit_score: int | None = None
    sponsorship_risk: str | None = None
    recommendation: str | None = None
    next_action: str | None = None
    notes: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    status: str
    fit_score: int | None
    sponsorship_risk: str | None
    recommendation: str | None
    next_action: str | None
    notes: str | None
