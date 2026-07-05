"""Evaluation API routes."""
from fastapi import APIRouter, Request, HTTPException
from .service import get_status, evaluate_job
from .schemas import EvaluationRunRequest

from urllib.parse import urlparse

router = APIRouter(tags=["evaluation"])


def _require_local_intent(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed")
    origin = request.headers.get("origin")
    if origin and (urlparse(origin).hostname or "").lower() not in {"localhost", "127.0.0.1"}:
        raise HTTPException(403, "Cross-site requests are not allowed")


@router.get("/evaluation/status")
def evaluation_status():
    return get_status()


@router.post("/jobs/{job_id}/evaluate")
def run_evaluation(job_id: int, data: EvaluationRunRequest, request: Request):
    _require_local_intent(request)
    result = evaluate_job(job_id, auto_generate_pack=data.auto_generate_pack)
    if not result.get("ok"):
        code = result.get("code", "")
        if code == "job_not_found":
            raise HTTPException(status_code=404, detail=result.get("error", "Job not found"))
        return result
    return result
