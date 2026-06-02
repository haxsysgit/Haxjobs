from sqlalchemy.orm import Session

from haxjobs_api.features.tasks.models import HermesTask, TaskStatus
from haxjobs_api.features.tasks.schemas import HermesTaskCreate


def create_hermes_task(session: Session, payload: HermesTaskCreate) -> HermesTask:
    task = HermesTask(status=TaskStatus.PENDING.value, **payload.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
