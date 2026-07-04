"""Packs API routes."""
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from .service import get_pack_status, generate_pack

router = APIRouter(tags=["packs"])


def _require_local_intent(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed")
    origin = request.headers.get("origin")
    if origin and (urlparse(origin).hostname or "").lower() not in {"localhost", "127.0.0.1"}:
        raise HTTPException(403, "Cross-site requests are not allowed")


@router.get("/jobs/{job_id}/pack")
def pack_status(job_id: int):
    return get_pack_status(job_id)


@router.post("/jobs/{job_id}/pack")
def create_pack(job_id: int, request: Request):
    _require_local_intent(request)
    return generate_pack(job_id)
