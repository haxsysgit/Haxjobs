from pydantic import BaseModel, ConfigDict, HttpUrl


class JobCreate(BaseModel):
    company: str
    title: str
    location: str | None = None
    source_platform: str = "manual"
    source_url: HttpUrl | str | None = None
    job_description: str | None = None
    salary_text: str | None = None
    work_mode: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    sponsorship_signal: str | None = None
    next_action: str | None = None
    notes: str | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company: str
    title: str
    location: str | None
    source_platform: str
    source_url: str | None
    job_description: str | None
    status: str


class ManualJobCreate(JobCreate):
    create_application: bool = True
