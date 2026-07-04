"""Discovery API routes."""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request

from .schemas import DiscoveryRunResponse, DiscoveryStatusResponse, DiscoveredJobResponse
from .service import get_new_jobs, get_status, run_discovery

router = APIRouter(tags=["discovery"])


def _require_local_intent(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed")
    origin = request.headers.get("origin")
    if origin and (urlparse(origin).hostname or "").lower() not in {"localhost", "127.0.0.1"}:
        raise HTTPException(403, "Cross-site requests are not allowed")


@router.post("/discovery/run")
def discovery_run(request: Request) -> DiscoveryRunResponse:
    _require_local_intent(request)
    return DiscoveryRunResponse(run_id=run_discovery(), running=True)


@router.get("/discovery/status")
def discovery_status() -> DiscoveryStatusResponse:
    return DiscoveryStatusResponse(**get_status())


@router.get("/discovery/jobs/new")
def discovery_new_jobs(since: str = "") -> list[DiscoveredJobResponse]:
    return [DiscoveredJobResponse(**job) for job in get_new_jobs(since)]
