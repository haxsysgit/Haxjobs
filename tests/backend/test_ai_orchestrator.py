from types import SimpleNamespace

from app.core.config import Settings
from app.models.analysis import AnalysisMetadata
from app.services.ai_orchestrator import AIPipeline, RecruiterStageOutput
from app.services.analysis import analyze_texts
from app.services.reporting import response_from_report


def make_base_analysis():
    cv_text = """
PROFESSIONAL SUMMARY
Python engineer with FastAPI and testing experience.

CORE SKILLS
Python, FastAPI, Vue

PROFESSIONAL EXPERIENCE
- Built API services and internal workflow tooling.
""".strip()
    jd_text = """
Backend Engineer
The Role
Strong Python fundamentals
Production API delivery
Vue exposure
""".strip()
    report = analyze_texts(cv_text=cv_text, jd_text=jd_text)
    return response_from_report(
        report,
        metadata=AnalysisMetadata(
            mode="stretch",
            source="upload",
            cv_label="sample_cv.txt",
            jd_label="sample_jd.txt",
        ),
    )


def test_ai_pipeline_fallback_mode_without_openai_key() -> None:
    pipeline = AIPipeline(Settings(openai_api_key=None))
    result = pipeline.enrich_analysis(make_base_analysis())
    assert result.recruiter_assessment.model_tier == "fallback"
    assert result.evaluator_assessment.model_tier == "fallback"
    assert result.verification_questions
    assert result.aspirational_pack.non_submittable is True


def test_ai_pipeline_uses_all_stages_when_model_calls_succeed(monkeypatch) -> None:
    pipeline = AIPipeline(Settings(openai_api_key="test-key"))
    pipeline.client = object()
    calls: list[str] = []

    def fake_structured_stage_call(*, model: str, instructions: str, payload: dict[str, object], schema):
        del payload
        calls.append(model)
        if "recruiter_agent" in instructions:
            return schema(
                shortlist_summary="Top shortlist criteria extracted.",
                priority_requirements=["Strong Python fundamentals"],
                concerns=["Code quality"],
            )
        if "evaluator_agent" in instructions:
            return schema(
                fit_score=79,
                summary="Evaluator stage complete.",
                weak_claims=[
                    {
                        "requirement_id": "req-1",
                        "requirement_text": "Strong Python fundamentals",
                        "issue": "Needs a concrete metric.",
                        "severity": "medium",
                    }
                ],
                uncertain_claims=[
                    {
                        "requirement_id": "req-2",
                        "requirement_text": "Production API delivery",
                        "issue": "Needs user confirmation.",
                        "severity": "high",
                    }
                ],
            )
        if "verification_agent" in instructions:
            return schema(
                verification_questions=[
                    {
                        "requirement_id": "req-2",
                        "requirement_text": "Production API delivery",
                        "question": "Can you provide a production API rollout example?",
                        "reason": "Current evidence is weak.",
                        "priority": "high",
                    }
                ]
            )
        if "applicant_agent" in instructions:
            return schema(
                tailored_cv_markdown="# Aspirational CV\n\n- Sample.",
                cover_letter_markdown="# Aspirational Cover Letter",
                interview_notes_markdown="# Aspirational Interview Notes",
            )
        return None

    monkeypatch.setattr(pipeline, "_structured_stage_call", fake_structured_stage_call)
    result = pipeline.enrich_analysis(make_base_analysis())

    assert calls == [
        pipeline.settings.ai_model_recruiter,
        pipeline.settings.ai_model_evaluator,
        pipeline.settings.ai_model_verifier,
        pipeline.settings.ai_model_applicant,
    ]
    assert result.recruiter_assessment.model_tier == pipeline.settings.ai_model_recruiter
    assert result.evaluator_assessment.model_tier == pipeline.settings.ai_model_evaluator
    assert result.verification_questions[0].model_tier == pipeline.settings.ai_model_verifier
    assert result.aspirational_pack.model_tier == pipeline.settings.ai_model_applicant


def test_structured_stage_call_uses_responses_parse() -> None:
    pipeline = AIPipeline(Settings(openai_api_key="test-key"))

    class DummyResponses:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def parse(self, **kwargs):
            self.calls.append(kwargs)
            schema = kwargs["text_format"]
            return SimpleNamespace(output_parsed=schema(shortlist_summary="ok", priority_requirements=[], concerns=[]))

    responses = DummyResponses()
    pipeline.client = SimpleNamespace(responses=responses)

    result = pipeline._structured_stage_call(
        model="gpt-5.4-mini",
        instructions="You are recruiter_agent.",
        payload={"role_title": "Backend Engineer"},
        schema=RecruiterStageOutput,
    )

    assert result is not None
    assert result.shortlist_summary == "ok"
    assert responses.calls[0]["text_format"] is RecruiterStageOutput
    assert responses.calls[0]["input"] == '{"role_title": "Backend Engineer"}'
