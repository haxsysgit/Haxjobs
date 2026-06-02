from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    application_pack_id: str
    document_type: str
    format: str
    path: str
    version: str = "1"
    is_submitted_version: bool = False


class DocumentRead(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
