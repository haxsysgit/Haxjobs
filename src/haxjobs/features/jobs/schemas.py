"""Job request/response schemas."""
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    status: str = "pending"
    source: str | None = None
    discovered_at: str | None = None
    role_family: str | None = None
    fit_score: int | None = None
    fit_level: int | None = None
    # ponytail: flat schema, add explicit nesting when frontend outgrows it
