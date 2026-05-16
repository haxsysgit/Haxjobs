from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeVar

from app.core.config import Settings
from app.models.analysis import (
    AnalyzeResponse,
    AspirationalPack,
    EvaluatorAssessment,
    EvaluatorFlag,
    RecruiterAssessment,
    VerificationQuestion,
)
from pydantic import BaseModel, Field
from app.services.generation import generate_application_pack

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - import guarded for local envs without optional dependency.
    OpenAI = None  # type: ignore[assignment]


@dataclass
class AIPipelineResult:
    recruiter_assessment: RecruiterAssessment
    evaluator_assessment: EvaluatorAssessment
    verification_questions: list[VerificationQuestion]
    aspirational_pack: AspirationalPack


class RecruiterStageOutput(BaseModel):
    shortlist_summary: str
    priority_requirements: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class EvaluatorFlagOutput(BaseModel):
    requirement_id: str
    requirement_text: str
    issue: str
    severity: str = "medium"


class EvaluatorStageOutput(BaseModel):
    fit_score: int
    summary: str
    weak_claims: list[EvaluatorFlagOutput] = Field(default_factory=list)
    uncertain_claims: list[EvaluatorFlagOutput] = Field(default_factory=list)


class VerificationQuestionOutput(BaseModel):
    requirement_id: str
    requirement_text: str
    question: str
    reason: str
    priority: str = "medium"


class VerificationStageOutput(BaseModel):
    verification_questions: list[VerificationQuestionOutput] = Field(default_factory=list)


class ApplicantStageOutput(BaseModel):
    tailored_cv_markdown: str
    cover_letter_markdown: str
    interview_notes_markdown: str


StageOutputT = TypeVar("StageOutputT", bound=BaseModel)


class AIPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = self._build_client(settings)

    def enrich_analysis(self, analysis: AnalyzeResponse) -> AIPipelineResult:
        recruiter = self._recruiter_stage(analysis)
        evaluator = self._evaluator_stage(analysis)
        verification = self._verification_stage(analysis, evaluator)
        aspirational = self._applicant_stage(analysis)
        return AIPipelineResult(
            recruiter_assessment=recruiter,
            evaluator_assessment=evaluator,
            verification_questions=verification,
            aspirational_pack=aspirational,
        )

    def _build_client(self, settings: Settings):
        if not settings.llm_configured or OpenAI is None:
            return None
        return OpenAI(api_key=settings.openai_api_key)

    def _recruiter_stage(self, analysis: AnalyzeResponse) -> RecruiterAssessment:
        fallback = RecruiterAssessment(
            shortlist_summary=(
                f"Role focus: {analysis.jd_analysis.role_title}. Prioritize the highest-signal requirements "
                "and keep low-evidence claims explicit."
            ),
            priority_requirements=[
                item.requirement_text for item in analysis.evidence_map[:4]
            ],
            concerns=analysis.jd_analysis.recruiter_concerns[:3],
            model_tier="fallback",
        )
        if self.client is None:
            return fallback

        payload = {
            "role_title": analysis.jd_analysis.role_title,
            "requirements": [
                {
                    "text": item.requirement_text,
                    "importance": item.importance,
                    "match_label": item.match_label,
                }
                for item in analysis.evidence_map
            ],
            "recruiter_concerns": analysis.jd_analysis.recruiter_concerns,
        }
        response = self._structured_stage_call(
            model=self.settings.ai_model_recruiter,
            instructions=(
                "You are recruiter_agent. Return compact JSON only with keys: "
                "shortlist_summary (string), priority_requirements (string[]), concerns (string[])."
            ),
            payload=payload,
            schema=RecruiterStageOutput,
        )
        if not response:
            return fallback
        return RecruiterAssessment(
            shortlist_summary=response.shortlist_summary or fallback.shortlist_summary,
            priority_requirements=response.priority_requirements[:6],
            concerns=response.concerns[:6],
            model_tier=self.settings.ai_model_recruiter,
        )

    def _evaluator_stage(self, analysis: AnalyzeResponse) -> EvaluatorAssessment:
        weak_matches = [
            match
            for match in analysis.evidence_map
            if match.match_label in {"Weak Match", "Gap"}
            or match.claim_label in {"Needs User Confirmation", "Stretch Wording", "Unsafe Claim"}
        ]
        fallback_flags = [
            EvaluatorFlag(
                requirement_id=match.requirement_id,
                requirement_text=match.requirement_text,
                issue=match.risk_warning or match.suggested_safe_wording,
                severity="high" if match.match_label == "Gap" else "medium",
            )
            for match in weak_matches[:8]
        ]
        fallback = EvaluatorAssessment(
            fit_score=analysis.fit_summary.score,
            summary=(
                "Evaluator pass completed with deterministic evidence-map checks. "
                "Weak or uncertain claims were flagged for confirmation."
            ),
            weak_claims=fallback_flags,
            uncertain_claims=fallback_flags,
            model_tier="fallback",
        )
        if self.client is None:
            return fallback

        payload = {
            "fit_score": analysis.fit_summary.score,
            "fit_summary": analysis.fit_summary.summary,
            "evidence_map": [item.model_dump(mode="json") for item in analysis.evidence_map],
            "warnings": analysis.warnings,
        }
        response = self._structured_stage_call(
            model=self.settings.ai_model_evaluator,
            instructions=(
                "You are evaluator_agent. Return compact JSON with keys: fit_score (int), summary (string), "
                "weak_claims (array of objects {requirement_id, requirement_text, issue, severity}), "
                "uncertain_claims (same schema)."
            ),
            payload=payload,
            schema=EvaluatorStageOutput,
        )
        if not response:
            return fallback

        return EvaluatorAssessment(
            fit_score=response.fit_score or analysis.fit_summary.score,
            summary=response.summary or fallback.summary,
            weak_claims=_parse_flags(response.weak_claims),
            uncertain_claims=_parse_flags(response.uncertain_claims),
            model_tier=self.settings.ai_model_evaluator,
        )

    def _verification_stage(
        self, analysis: AnalyzeResponse, evaluator: EvaluatorAssessment
    ) -> list[VerificationQuestion]:
        fallback: list[VerificationQuestion] = [
            VerificationQuestion(
                requirement_id=item.requirement_id,
                requirement_text=item.requirement_text,
                question=item.question,
                reason=item.reason,
                priority=item.priority,
                model_tier="fallback",
            )
            for item in analysis.follow_up_questions
        ]
        if self.client is None:
            return fallback

        payload = {
            "follow_up_questions": [item.model_dump(mode="json") for item in analysis.follow_up_questions],
            "uncertain_claims": [item.model_dump(mode="json") for item in evaluator.uncertain_claims],
        }
        response = self._structured_stage_call(
            model=self.settings.ai_model_verifier,
            instructions=(
                "You are verification_agent. Return JSON with key verification_questions as an array of objects "
                "{requirement_id, requirement_text, question, reason, priority}."
            ),
            payload=payload,
            schema=VerificationStageOutput,
        )
        if not response:
            return fallback

        parsed: list[VerificationQuestion] = []
        for item in response.verification_questions:
            parsed.append(
                VerificationQuestion(
                    requirement_id=item.requirement_id or "",
                    requirement_text=item.requirement_text or "Requirement",
                    question=item.question or "Can you confirm this claim with a concrete example?",
                    reason=item.reason or "Additional verification is required.",
                    priority=_coerce_priority(item.priority),
                    model_tier=self.settings.ai_model_verifier,
                )
            )
        return parsed or fallback

    def _applicant_stage(self, analysis: AnalyzeResponse) -> AspirationalPack:
        ideal_analysis = analysis.model_copy(
            deep=True,
            update={
                "metadata": analysis.metadata.model_copy(update={"mode": "ideal"})
            },
        )
        aspirational_pack = generate_application_pack(analysis=ideal_analysis)
        fallback = AspirationalPack(
            tailored_cv_markdown=aspirational_pack.tailored_cv_markdown,
            cover_letter_markdown=aspirational_pack.cover_letter_markdown,
            interview_notes_markdown=aspirational_pack.interview_notes_markdown,
            model_tier="fallback",
        )
        if self.client is None:
            return fallback

        payload = {
            "role_title": analysis.jd_analysis.role_title,
            "tailored_cv_markdown": aspirational_pack.tailored_cv_markdown,
            "cover_letter_markdown": aspirational_pack.cover_letter_markdown,
            "interview_notes_markdown": aspirational_pack.interview_notes_markdown,
            "label_requirement": "Keep output clearly aspirational and non-submittable.",
        }
        response = self._structured_stage_call(
            model=self.settings.ai_model_applicant,
            instructions=(
                "You are applicant_agent. Refine the aspirational sample and return JSON with keys "
                "tailored_cv_markdown, cover_letter_markdown, interview_notes_markdown. "
                "Never present the output as already verified."
            ),
            payload=payload,
            schema=ApplicantStageOutput,
        )
        if not response:
            return fallback

        return AspirationalPack(
            tailored_cv_markdown=response.tailored_cv_markdown or aspirational_pack.tailored_cv_markdown,
            cover_letter_markdown=response.cover_letter_markdown or aspirational_pack.cover_letter_markdown,
            interview_notes_markdown=response.interview_notes_markdown or aspirational_pack.interview_notes_markdown,
            model_tier=self.settings.ai_model_applicant,
        )

    def _structured_stage_call(
        self,
        *,
        model: str,
        instructions: str,
        payload: dict[str, object],
        schema: type[StageOutputT],
    ) -> StageOutputT | None:
        if self.client is None:
            return None
        try:
            response = self.client.responses.parse(
                model=model,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=True),
                text_format=schema,
                max_output_tokens=700,
            )
            return response.output_parsed
        except Exception:
            return None


def _parse_flags(items: list[EvaluatorFlagOutput]) -> list[EvaluatorFlag]:
    parsed: list[EvaluatorFlag] = []
    for item in items:
        parsed.append(
            EvaluatorFlag(
                requirement_id=item.requirement_id or "",
                requirement_text=item.requirement_text or "Requirement",
                issue=item.issue or "Needs verification.",
                severity=_coerce_priority(item.severity),
            )
        )
    return parsed


def _coerce_priority(value: Any) -> str:
    if value in {"high", "medium", "low"}:
        return value
    return "medium"
