"""Decisions API routes."""
from fastapi import APIRouter, Query, Request, HTTPException
from .service import get_decisions, record_decision
from .schemas import DecisionRequest

from urllib.parse import urlparse

router = APIRouter(tags=["decisions"])


def _require_local_intent(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed")
    origin = request.headers.get("origin")
    if origin and (urlparse(origin).hostname or "").lower() not in {"localhost", "127.0.0.1"}:
        raise HTTPException(403, "Cross-site requests are not allowed")


@router.get("/decisions")
def list_decisions(job_id: int | None = Query(None)):
    return {"decisions": get_decisions(job_id=job_id)}


@router.post("/decisions")
def create_decision(data: DecisionRequest, request: Request):
    _require_local_intent(request)
    result = record_decision(data.job_id, data.decision, data.reason)
    if not result.get("ok"):
        code = result.get("code", "")
        if code == "job_not_found":
            raise HTTPException(status_code=404, detail=result.get("error", "Job not found"))
        if code == "invalid_decision":
            raise HTTPException(status_code=400, detail=result.get("error", "Bad decision"))
        return result
    return result
