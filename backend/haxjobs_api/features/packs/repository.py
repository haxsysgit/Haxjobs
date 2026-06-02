from sqlalchemy.orm import Session

from haxjobs_api.features.packs.models import ApplicationPack
from haxjobs_api.features.packs.schemas import ApplicationPackCreate


def create_application_pack(session: Session, payload: ApplicationPackCreate) -> ApplicationPack:
    pack = ApplicationPack(**payload.model_dump())
    session.add(pack)
    session.commit()
    session.refresh(pack)
    return pack
