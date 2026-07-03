"""Discovery API routes."""
from __future__ import annotations

from fastapi import APIRouter

from .schemas import DiscoveryRunResponse, DiscoveryStatusResponse, DiscoveredJobResponse
from .service import get_new_jobs, get_status, run_discovery

router = APIRouter(tags=["discovery"])


@router.post("/discovery/run")
def discovery_run() -> DiscoveryRunResponse:
    return DiscoveryRunResponse(run_id=run_discovery(), running=True)


@router.get("/discovery/status")
def discovery_status() -> DiscoveryStatusResponse:
    return DiscoveryStatusResponse(**get_status())


@router.get("/discovery/jobs/new")
def discovery_new_jobs(since: str = "") -> list[DiscoveredJobResponse]:
    return [DiscoveredJobResponse(**job) for job in get_new_jobs(since)]
