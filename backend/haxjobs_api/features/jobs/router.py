from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from haxjobs_api.database import get_db_session
from haxjobs_api.features.applications.schemas import ApplicationRead
from haxjobs_api.features.jobs.repository import create_manual_job, get_job, list_jobs
from haxjobs_api.features.jobs.schemas import JobRead, ManualJobCreate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def serialize_snapshot(snapshot):
    return {
        "id": snapshot.id,
        "job_id": snapshot.job_id,
        "url": snapshot.url,
        "title": snapshot.title,
        "source_platform": snapshot.source_platform,
    }


def serialize_status_event(event):
    return {
        "id": event.id,
        "application_id": event.application_id,
        "job_id": event.job_id,
        "event_type": event.event_type,
        "summary": event.summary,
    }


@router.post("/manual", status_code=status.HTTP_201_CREATED)
def save_manual_job(payload: ManualJobCreate, session: Session = Depends(get_db_session)):
    job, application, snapshot, event = create_manual_job(session, payload)
    return {
        **JobRead.model_validate(job).model_dump(),
        "application": ApplicationRead.model_validate(application).model_dump() if application else None,
        "snapshot": serialize_snapshot(snapshot),
        "status_event": serialize_status_event(event),
    }


@router.get("", response_model=list[JobRead])
def read_jobs(session: Session = Depends(get_db_session)):
    return list_jobs(session)


@router.get("/{job_id}", response_model=JobRead)
def read_job(job_id: str, session: Session = Depends(get_db_session)):
    job = get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
