from sqlalchemy import select
from sqlalchemy.orm import Session

from haxjobs_api.features.applications.models import Application, ApplicationStatus
from haxjobs_api.features.jobs.models import Job, JobSourceSnapshot
from haxjobs_api.features.jobs.schemas import ManualJobCreate
from haxjobs_api.features.tasks.models import StatusEvent


def create_manual_job(session: Session, payload: ManualJobCreate) -> tuple[Job, Application | None, JobSourceSnapshot, StatusEvent]:
    """Save a manually captured job and create the first workflow records.

    Manual save is the 0.1.x bridge before browser-extension capture exists.
    It creates a source snapshot and timeline event immediately so future Hermes
    analysis has traceable source context.
    """

    job = Job(
        company=payload.company,
        title=payload.title,
        location=payload.location,
        source_platform=payload.source_platform,
        source_url=str(payload.source_url) if payload.source_url else None,
        job_description=payload.job_description,
        salary_text=payload.salary_text,
        work_mode=payload.work_mode,
        seniority=payload.seniority,
        employment_type=payload.employment_type,
        sponsorship_signal=payload.sponsorship_signal,
    )
    snapshot = JobSourceSnapshot(
        job=job,
        url=str(payload.source_url) if payload.source_url else None,
        title=payload.title,
        source_platform=payload.source_platform,
        visible_text=payload.job_description,
        user_note=payload.notes,
    )
    application = None
    if payload.create_application:
        application = Application(
            job=job,
            status=ApplicationStatus.SAVED.value,
            next_action=payload.next_action,
            notes=payload.notes,
        )
    event = StatusEvent(
        job_id=None,
        application=application,
        event_type="job_saved",
        summary=f"Saved {payload.title} at {payload.company}",
        metadata_json={"source_platform": payload.source_platform},
    )
    session.add_all([job, snapshot, event])
    session.commit()
    session.refresh(job)
    session.refresh(snapshot)
    if application:
        session.refresh(application)
        event.application_id = application.id
        event.job_id = job.id
        session.commit()
        session.refresh(event)
    return job, application, snapshot, event


def list_jobs(session: Session) -> list[Job]:
    return list(session.scalars(select(Job).order_by(Job.created_at.desc())).all())


def get_job(session: Session, job_id: str) -> Job | None:
    return session.get(Job, job_id)
