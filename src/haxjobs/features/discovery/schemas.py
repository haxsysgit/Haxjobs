"""Discovery request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class DiscoveryRunResponse(BaseModel):
    run_id: str
    running: bool = True


class DiscoveryStatusResponse(BaseModel):
    running: bool = False
    run_id: str = ""
    found: int = 0
    new: int = 0
    promoted: int = 0
    errors: list[str] = []
    started_at: str = ""
    finished_at: str = ""


class DiscoveredJobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str = ""
    source_url: str = ""
    discovery_status: str = ""
    promoted_job_id: int | None = None
    created_at: str = ""
