from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from haxjobs_api.database import get_db_session
from haxjobs_api.features.packs.repository import create_application_pack
from haxjobs_api.features.packs.schemas import ApplicationPackCreate, ApplicationPackRead

router = APIRouter(prefix="/api/application-packs", tags=["application-packs"])


@router.post("", response_model=ApplicationPackRead, status_code=status.HTTP_201_CREATED)
def add_application_pack(payload: ApplicationPackCreate, session: Session = Depends(get_db_session)):
    return create_application_pack(session, payload)
