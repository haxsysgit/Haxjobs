from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.analysis import AnalyzeResponse, DEFAULT_MODE, MODE_OPTIONS
from app.services.documents import UnsupportedDocumentError, extract_text_from_upload
from app.services.workflow import analyze_upload

router = APIRouter(tags=["analysis"])


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(
    cv_file: UploadFile = File(...),
    jd_text: str = Form(...),
    mode: MODE_OPTIONS = Form(DEFAULT_MODE),
) -> AnalyzeResponse:
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is required.")
    try:
        cv_text = extract_text_from_upload(cv_file.filename or "cv", await cv_file.read())
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return analyze_upload(
        cv_text=cv_text,
        jd_text=jd_text.strip(),
        mode=mode,
        cv_label=cv_file.filename or "Uploaded CV",
    )
