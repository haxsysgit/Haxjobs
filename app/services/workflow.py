from __future__ import annotations

from pathlib import Path

from app.models.analysis import (
    AnalyzeProfileCvRequest,
    AnalysisMetadata,
    AnalysisMode,
    AnalysisReport,
    AnalyzeResponse,
    FollowUpAnswer,
    GenerateApplicationPackResponse,
    UserClaimConfirmation,
)
from app.core.config import get_settings
from app.services.analysis import analyze_texts
from app.services.ai_orchestrator import AIPipeline
from app.services.demo_fixtures import load_demo_texts
from app.services.generation import generate_application_pack
from app.services.profile_store import (
    get_cv_text,
    import_cv_documents,
    load_or_create_profile,
    record_analysis,
    save_profile,
)
from app.services.reporting import response_from_report


def analyze(cv_text: str, jd_text: str, mode: AnalysisMode = "stretch") -> AnalysisReport:
    """Shared deterministic workflow used by both the CLI and API."""
    del mode
    return analyze_texts(cv_text=cv_text, jd_text=jd_text)


def analyze_upload(cv_text: str, jd_text: str, mode: AnalysisMode, cv_label: str):
    report = analyze(cv_text=cv_text, jd_text=jd_text, mode=mode)
    response = response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode=mode,
            source="upload",
            cv_label=cv_label,
            jd_label="Pasted Job Description",
        ),
    )
    enriched = enrich_with_ai_pipeline(response)
    settings = get_settings()
    profile_path = Path(settings.profile_store_path)
    profile = load_or_create_profile(profile_path)
    profile = import_cv_documents(profile, [(cv_label, cv_text)])
    profile = record_analysis(profile, enriched)
    save_profile(profile_path, profile)
    return enriched


def analyze_demo(cv_fixture_id: str, jd_fixture_id: str, mode: AnalysisMode):
    cv_text, jd_text, cv_label, jd_label = load_demo_texts(cv_fixture_id, jd_fixture_id)
    report = analyze(cv_text=cv_text, jd_text=jd_text, mode=mode)
    response = response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode=mode,
            source="demo",
            cv_label=cv_label,
            jd_label=jd_label,
        ),
    )
    return enrich_with_ai_pipeline(response)


def analyze_saved_cv(payload: AnalyzeProfileCvRequest) -> AnalyzeResponse:
    settings = get_settings()
    profile_path = Path(settings.profile_store_path)
    profile = load_or_create_profile(profile_path)
    cv_text = get_cv_text(profile, payload.cv_document_id)
    profile_text = _compose_profile_first_cv_text(profile, cv_text)
    report = analyze(cv_text=profile_text, jd_text=payload.jd_text.strip(), mode=payload.mode)
    selected_label = next(
        item.label for item in profile.cv_documents if item.id == payload.cv_document_id
    )
    response = response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode=payload.mode,
            source="upload",
            cv_label=selected_label,
            jd_label="Pasted Job Description",
        ),
    )
    enriched = enrich_with_ai_pipeline(response)
    profile = record_analysis(profile, enriched)
    save_profile(profile_path, profile)
    return enriched


def _compose_profile_first_cv_text(profile, selected_cv_text: str) -> str:
    """Give analysis the selected CV plus reusable profile memory.

    The public UX is profile-first. This keeps the backend aligned without changing
    the deterministic analyzer contract yet.
    """
    facts = [fact.text for fact in profile.evidence_library[:80] if fact.text.strip()]
    skills = ", ".join(profile.top_skills)
    sections = [selected_cv_text.strip()]
    if profile.summary.strip():
        sections.append(f"Reusable profile summary:\n{profile.summary.strip()}")
    if skills:
        sections.append(f"Reusable profile skills:\n{skills}")
    if facts:
        sections.append("Reusable profile facts:\n" + "\n".join(f"- {fact}" for fact in facts))
    return "\n\n".join(section for section in sections if section.strip())


def generate_pack_from_analysis(
    analysis: AnalyzeResponse,
    follow_up_answers: list[FollowUpAnswer] | None = None,
    user_claim_confirmations: list[UserClaimConfirmation] | None = None,
    user_notes: str | None = None,
) -> GenerateApplicationPackResponse:
    return generate_application_pack(
        analysis=analysis,
        follow_up_answers=follow_up_answers,
        user_claim_confirmations=user_claim_confirmations,
        user_notes=user_notes,
    )


def enrich_with_ai_pipeline(analysis: AnalyzeResponse) -> AnalyzeResponse:
    pipeline = AIPipeline(get_settings())
    ai_result = pipeline.enrich_analysis(analysis)
    return analysis.model_copy(
        update={
            "analysis_engine": "ai",
            "recruiter_assessment": ai_result.recruiter_assessment,
            "evaluator_assessment": ai_result.evaluator_assessment,
            "verification_questions": ai_result.verification_questions,
            "aspirational_pack": ai_result.aspirational_pack,
        }
    )
