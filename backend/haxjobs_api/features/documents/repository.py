from sqlalchemy.orm import Session

from haxjobs_api.features.documents.models import Document
from haxjobs_api.features.documents.schemas import DocumentCreate


def create_document(session: Session, payload: DocumentCreate) -> Document:
    document = Document(**payload.model_dump())
    session.add(document)
    session.commit()
    session.refresh(document)
    return document
