"""Onboarding API routes."""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from .schemas import (
    CVUploadResponse,
    FieldQuestion,
    OnboardingStatusResponse,
    TextUploadRequest,
    WizardAnswer,
    WizardResponse,
)
from .service import (
    apply_answer,
    clear_session,
    extract_text_from_upload,
    get_next_question,
    get_session,
    load_profile,
    process_cv,
    save_profile,
    start_session,
)

router = APIRouter(tags=["onboarding"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_CV_LENGTH = 100  # minimum chars for meaningful extraction


def _require_local_intent(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed")
    origin = request.headers.get("origin")
    if origin and (urlparse(origin).hostname or "").lower() not in {"localhost", "127.0.0.1"}:
        raise HTTPException(403, "Cross-site requests are not allowed")


@router.get("/onboarding/status")
def onboarding_status() -> OnboardingStatusResponse:
    profile = load_profile()
    if profile:
        return OnboardingStatusResponse(stage="complete", has_profile=True)
    pending, phase, _ = get_session()
    if pending:
        return OnboardingStatusResponse(stage=phase, has_profile=True)
    return OnboardingStatusResponse(stage="not_started", has_profile=False)


@router.post("/onboarding/upload")
async def onboarding_upload(request: Request, file: UploadFile = File(...)) -> CVUploadResponse:
    _require_local_intent(request)
    if not file.filename:
        raise HTTPException(400, "No file provided")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        text = extract_text_from_upload(content, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if len(text) < MIN_CV_LENGTH:
        raise HTTPException(400, "CV text too short — couldn't extract meaningful content")

    try:
        profile, questions, phases = process_cv(text)
    except RuntimeError as e:
        raise HTTPException(503, f"Provider not configured: {e}")
    except ValueError as e:
        raise HTTPException(400, f"CV processing failed: {e}")
    except Exception as e:
        raise HTTPException(502, f"Agent call failed: {e}")

    start_session(profile, questions)
    next_q = get_next_question(profile)
    _, phase, remaining = get_session()

    next_question = None
    if next_q:
        next_question = FieldQuestion(**next_q)  # type: ignore[arg-type]

    return CVUploadResponse(
        profile=profile,
        next_question=next_question,
        questions_remaining=remaining,
        phase=phase,
        extraction_phases=phases,
    )


@router.post("/onboarding/extract-text")
def onboarding_extract_text(body: TextUploadRequest, request: Request) -> CVUploadResponse:
    _require_local_intent(request)
    text = body.text.strip()
    if len(text) < MIN_CV_LENGTH:
        raise HTTPException(400, "CV text too short — couldn't extract meaningful content")

    try:
        profile, questions, phases = process_cv(text)
    except RuntimeError as e:
        raise HTTPException(503, f"Provider not configured: {e}")
    except ValueError as e:
        raise HTTPException(400, f"CV processing failed: {e}")
    except Exception as e:
        raise HTTPException(502, f"Agent call failed: {e}")

    start_session(profile, questions)
    next_q = get_next_question(profile)
    _, phase, remaining = get_session()

    next_question = None
    if next_q:
        next_question = FieldQuestion(**next_q)  # type: ignore[arg-type]

    return CVUploadResponse(
        profile=profile,
        next_question=next_question,
        questions_remaining=remaining,
        phase=phase,
        extraction_phases=phases,
    )


@router.post("/onboarding/wizard")
def onboarding_wizard(answer: WizardAnswer, request: Request) -> WizardResponse:
    _require_local_intent(request)
    profile, _, _ = get_session()
    if profile is None:
        raise HTTPException(400, "No active onboarding session. Upload a CV first.")

    apply_answer(profile, answer.question_id, answer.answer)
    next_q = get_next_question(profile)
    _, phase, remaining = get_session()

    next_question = None
    if next_q:
        next_question = FieldQuestion(**next_q)  # type: ignore[arg-type]

    return WizardResponse(
        profile=profile,
        next_question=next_question,
        questions_remaining=remaining,
        phase=phase,
    )


@router.post("/onboarding/complete")
def onboarding_complete(request: Request) -> dict:
    _require_local_intent(request)
    profile, _, _ = get_session()
    if profile is None:
        raise HTTPException(400, "No active onboarding session.")

    profile["onboarding_complete"] = True
    save_profile(profile)
    clear_session()
    return {"ok": True, "stage": "complete"}


@router.get("/onboarding/reset")
def onboarding_reset_get() -> dict:
    raise HTTPException(405, "Use POST /onboarding/reset")


@router.post("/onboarding/reset")
def onboarding_reset(request: Request) -> dict:
    """Reset all onboarding state — clears in-memory session and persisted profile."""
    _require_local_intent(request)
    from .service import delete_profile, clear_session

    clear_session()
    delete_profile()
    return {"ok": True, "stage": "not_started"}
