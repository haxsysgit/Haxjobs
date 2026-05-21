from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

MatchLabel = Literal[
    "Strong Match",
    "Partial Match",
    "Transferable Match",
    "Weak Match",
    "Gap",
]
ClaimLabel = Literal[
    "Confirmed",
    "Inferred",
    "Needs User Confirmation",
    "Stretch Wording",
    "Unsafe Claim",
]
ImportanceLabel = Literal["required", "nice_to_have"]
PriorityLabel = Literal["high", "medium", "low"]
AnalysisMode = Literal["safe", "stretch", "interview", "ideal"]
AnalysisSource = Literal["upload", "demo"]
MODE_OPTIONS = Literal["safe", "stretch", "interview", "ideal"]
AnalysisEngine = Literal["ai"]
ClaimConfirmationStatus = Literal["confirmed", "rejected", "uncertain"]
DEFAULT_MODE: AnalysisMode = "stretch"


class AnalysisMetadata(BaseModel):
    mode: AnalysisMode
    source: AnalysisSource
    cv_label: str
    jd_label: str


class DemoFixtureOption(BaseModel):
    id: str
    label: str


class FitSummary(BaseModel):
    score: int
    label: str
    matched_requirements: int
    total_requirements: int
    summary: str


class JDRequirement(BaseModel):
    id: str
    text: str
    section: str
    importance: ImportanceLabel
    category: str
    keywords: list[str] = Field(default_factory=list)


class JDAnalysis(BaseModel):
    role_title: str
    section_titles: list[str] = Field(default_factory=list)
    requirements: list[JDRequirement] = Field(default_factory=list)
    recruiter_concerns: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    desirable_skills: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    id: str
    category: str
    source_section: str
    evidence: str
    keywords: list[str] = Field(default_factory=list)


class EvidenceMatch(BaseModel):
    requirement_id: str
    requirement_text: str
    section: str
    importance: ImportanceLabel
    match_label: MatchLabel
    claim_label: ClaimLabel
    supporting_evidence: list[str] = Field(default_factory=list)
    suggested_safe_wording: str
    risk_warning: str | None = None


class FollowUpQuestion(BaseModel):
    requirement_id: str
    requirement_text: str
    question: str
    reason: str
    priority: PriorityLabel


class SurveyChoice(BaseModel):
    id: str
    label: str
    description: str


class SurveyQuestion(BaseModel):
    question_id: str
    requirement_id: str
    requirement_text: str
    prompt: str
    helper_text: str
    priority: PriorityLabel
    choices: list[SurveyChoice] = Field(default_factory=list)
    allow_notes: bool = True


class RecruiterAssessment(BaseModel):
    shortlist_summary: str
    priority_requirements: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    model_tier: str = "fallback"


class EvaluatorFlag(BaseModel):
    requirement_id: str
    requirement_text: str
    issue: str
    severity: PriorityLabel = "medium"


class EvaluatorAssessment(BaseModel):
    fit_score: int
    summary: str
    weak_claims: list[EvaluatorFlag] = Field(default_factory=list)
    uncertain_claims: list[EvaluatorFlag] = Field(default_factory=list)
    model_tier: str = "fallback"


class VerificationQuestion(BaseModel):
    requirement_id: str
    requirement_text: str
    question: str
    reason: str
    priority: PriorityLabel = "medium"
    model_tier: str = "fallback"


class AspirationalPack(BaseModel):
    label: str = "Aspirational sample (non-submittable until user-confirmed)"
    non_submittable: bool = True
    tailored_cv_markdown: str
    cover_letter_markdown: str
    interview_notes_markdown: str
    model_tier: str = "fallback"


class AnalysisReport(BaseModel):
    fit_summary: FitSummary
    jd_analysis: JDAnalysis
    candidate_evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_map: list[EvidenceMatch] = Field(default_factory=list)
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    ok: bool = True
    analysis_engine: AnalysisEngine = "ai"
    metadata: AnalysisMetadata
    fit_summary: FitSummary
    jd_analysis: JDAnalysis
    candidate_evidence: list[EvidenceItem]
    evidence_map: list[EvidenceMatch]
    follow_up_questions: list[FollowUpQuestion]
    survey_questions: list[SurveyQuestion] = Field(default_factory=list)
    recruiter_assessment: RecruiterAssessment | None = None
    evaluator_assessment: EvaluatorAssessment | None = None
    verification_questions: list[VerificationQuestion] = Field(default_factory=list)
    aspirational_pack: AspirationalPack | None = None
    warnings: list[str]
    markdown_report: str


class FollowUpAnswer(BaseModel):
    requirement_id: str
    answer: str = ""
    skipped: bool = False


class UserClaimConfirmation(BaseModel):
    requirement_id: str
    status: ClaimConfirmationStatus
    notes: str = ""


class GenerateApplicationPackRequest(BaseModel):
    analysis: AnalyzeResponse
    follow_up_answers: list[FollowUpAnswer] = Field(default_factory=list)
    user_claim_confirmations: list[UserClaimConfirmation] = Field(default_factory=list)
    user_notes: str | None = None


class GenerationMetadata(BaseModel):
    mode: AnalysisMode
    role_title: str
    source: AnalysisSource
    aspirational: bool = False
    follow_up_answer_count: int = 0
    unanswered_follow_up_count: int = 0
    generated_documents: list[str] = Field(default_factory=list)


class GenerateApplicationPackResponse(BaseModel):
    metadata: GenerationMetadata
    tailored_cv_markdown: str
    cover_letter_markdown: str
    interview_notes_markdown: str
    evidence_map_json: list[EvidenceMatch]
    application_pack_json: dict[str, Any]


class AnalyzeDemoRequest(BaseModel):
    cv_fixture: str
    jd_fixture: str
    mode: AnalysisMode = DEFAULT_MODE


class AnalyzeProfileCvRequest(BaseModel):
    cv_document_id: str
    jd_text: str
    mode: AnalysisMode = DEFAULT_MODE


class DemoOptionsResponse(BaseModel):
    cv_fixtures: list[DemoFixtureOption]
    jd_fixtures: list[DemoFixtureOption]
    default_cv_fixture: str
    default_jd_fixture: str
    modes: list[AnalysisMode] = Field(default_factory=lambda: ["safe", "stretch", "interview", "ideal"])
