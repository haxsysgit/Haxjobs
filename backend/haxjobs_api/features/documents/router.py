from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from haxjobs_api.database import get_db_session
from haxjobs_api.features.documents.repository import create_document
from haxjobs_api.features.documents.schemas import DocumentCreate, DocumentRead, DocumentTextRegister
from haxjobs_api.services.storage import DocumentStorage, UnsafeDocumentPathError

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/register", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def register_existing_document(payload: DocumentCreate, session: Session = Depends(get_db_session)):
    return create_document(session, payload)


@router.post("/register-text", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def register_text_document(payload: DocumentTextRegister, session: Session = Depends(get_db_session)):
    try:
        path = DocumentStorage().write_text(payload.filename, payload.content)
    except UnsafeDocumentPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_payload = DocumentCreate(
        application_pack_id=payload.application_pack_id,
        document_type=payload.document_type,
        format=payload.format,
        path=str(path),
        version=payload.version,
        is_submitted_version=payload.is_submitted_version,
    )
    return create_document(session, document_payload)
