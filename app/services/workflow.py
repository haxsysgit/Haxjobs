from __future__ import annotations

from app.models.analysis import (
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
    return enrich_with_ai_pipeline(response)


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
