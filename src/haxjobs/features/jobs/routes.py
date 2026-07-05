"""Jobs API routes."""
from fastapi import APIRouter, Query, HTTPException
from .service import list_jobs, get_job_detail

router = APIRouter(tags=["jobs"])


@router.get("/jobs")
def get_jobs(
    status: str | None = Query(None),
    role_family: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1, le=100),
):
    rows = list_jobs(status_filter=status, role_family=role_family, offset=offset, limit=limit)
    return {"jobs": rows, "total": len(rows)}


@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: int):
    job = get_job_detail(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
