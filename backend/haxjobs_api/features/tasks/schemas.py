from pydantic import BaseModel, ConfigDict


class HermesTaskCreate(BaseModel):
    task_type: str
    job_id: str | None = None
    application_id: str | None = None
    contact_id: str | None = None
    profile_id: str | None = None
    pack_id: str | None = None
    input_payload_json: dict = {}


class HermesTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    status: str
    job_id: str | None
    application_id: str | None
    result_payload_json: dict | None
    error_message: str | None
