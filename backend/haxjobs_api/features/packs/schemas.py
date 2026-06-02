from pydantic import BaseModel, ConfigDict


class ApplicationPackCreate(BaseModel):
    application_id: str
    company: str
    role_title: str
    based_on_pack_id: str | None = None
    generation_mode: str | None = None
    fit_summary: str | None = None


class ApplicationPackRead(ApplicationPackCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
