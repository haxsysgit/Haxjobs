from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from haxjobs_api.database import get_db_session
from haxjobs_api.features.tasks.repository import create_hermes_task
from haxjobs_api.features.tasks.schemas import HermesTaskCreate, HermesTaskRead

router = APIRouter(prefix="/api/hermes-tasks", tags=["hermes-tasks"])


@router.post("", response_model=HermesTaskRead, status_code=status.HTTP_201_CREATED)
def add_hermes_task(payload: HermesTaskCreate, session: Session = Depends(get_db_session)):
    return create_hermes_task(session, payload)
