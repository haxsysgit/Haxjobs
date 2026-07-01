"""Pack request/response schemas."""
from pydantic import BaseModel


class PackResponse(BaseModel):
    job_id: int
    pack_status: str = "not_generated"
    pack_dir: str | None = None
