"""Onboarding API routes."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from .schemas import (
    CVUploadResponse,
    OnboardingStatusResponse,
    WizardAnswer,
    WizardResponse,
)
from .service import (
    apply_answer,
    clear_session,
    extract_profile_from_cv,
    extract_text_from_upload,
    get_next_question,
    get_session,
    load_profile,
    save_profile,
    start_session,
)

router = APIRouter(tags=["onboarding"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/onboarding/status")
def onboarding_status() -> OnboardingStatusResponse:
    profile = load_profile()
    if profile:
        return OnboardingStatusResponse(stage="complete", has_profile=True)
    pending, _ = get_session()
    if pending:
        return OnboardingStatusResponse(stage="wizard_in_progress", has_profile=True)
    return OnboardingStatusResponse(stage="not_started", has_profile=False)


@router.post("/onboarding/upload")
async def onboarding_upload(file: UploadFile = File(...)) -> CVUploadResponse:
    if not file.filename:
        raise HTTPException(400, "No file provided")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        text = extract_text_from_upload(content, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if len(text) < 50:
        raise HTTPException(400, "CV text too short — couldn't extract meaningful content")

    try:
        profile = extract_profile_from_cv(text)
    except RuntimeError as e:
        raise HTTPException(503, f"Provider not configured: {e}")
    except ValueError as e:
        raise HTTPException(400, f"Profile extraction failed: {e}")
    except Exception as e:
        raise HTTPException(502, f"Agent call failed: {e}")

    start_session(profile)
    next_q = get_next_question(profile, [])
    return CVUploadResponse(profile=profile, next_question=next_q)


@router.post("/onboarding/wizard")
def onboarding_wizard(answer: WizardAnswer) -> WizardResponse:
    profile, answered = get_session()
    if profile is None:
        raise HTTPException(400, "No active onboarding session. Upload a CV first.")

    apply_answer(profile, answer.question_id, answer.answer)
    answered.append(answer.question_id)
    next_q = get_next_question(profile, answered)
    return WizardResponse(
        profile=profile,
        next_question=next_q,
        stage="complete" if next_q is None else "wizard_in_progress",
    )


@router.post("/onboarding/complete")
def onboarding_complete() -> dict:
    profile, _ = get_session()
    if profile is None:
        raise HTTPException(400, "No active onboarding session.")

    save_profile(profile)
    clear_session()
    return {"ok": True, "stage": "complete"}
