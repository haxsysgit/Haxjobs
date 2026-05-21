from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.core.config import get_settings
from app.models.profile import CandidateProfile, ProfileExportBundle, SaveSurveyResponseRequest
from app.services.documents import extract_text_from_upload
from app.services.profile_store import (
    export_profile_bundle,
    import_profile_bundle,
    import_cv_documents,
    load_or_create_profile,
    save_profile,
    save_survey_response,
)

router = APIRouter(tags=["profile"])


@router.get("/api/profile", response_model=CandidateProfile)
def profile_read() -> CandidateProfile:
    settings = get_settings()
    return load_or_create_profile(Path(settings.profile_store_path))


@router.get("/api/profile/export", response_model=ProfileExportBundle)
def profile_export() -> ProfileExportBundle:
    settings = get_settings()
    profile = load_or_create_profile(Path(settings.profile_store_path))
    return export_profile_bundle(profile)


@router.post("/api/profile/upload-cvs", response_model=CandidateProfile)
async def upload_profile_cvs(
    cv_files: list[UploadFile] = File(...),
) -> CandidateProfile:
    settings = get_settings()
    profile_path = Path(settings.profile_store_path)
    profile = load_or_create_profile(profile_path)
    documents: list[tuple[str, str]] = []
    for cv_file in cv_files:
        text = extract_text_from_upload(cv_file.filename or "cv", await cv_file.read())
        documents.append((cv_file.filename or "Uploaded CV", text))
    profile = import_cv_documents(profile, documents)
    return save_profile(profile_path, profile)


@router.post("/api/profile/survey-response", response_model=CandidateProfile)
def profile_survey_response(payload: SaveSurveyResponseRequest) -> CandidateProfile:
    settings = get_settings()
    profile_path = Path(settings.profile_store_path)
    profile = load_or_create_profile(profile_path)
    profile = save_survey_response(profile, payload)
    return save_profile(profile_path, profile)


@router.post("/api/profile/import", response_model=CandidateProfile)
def profile_import(payload: ProfileExportBundle) -> CandidateProfile:
    settings = get_settings()
    profile_path = Path(settings.profile_store_path)
    profile = import_profile_bundle(payload)
    return save_profile(profile_path, profile)
