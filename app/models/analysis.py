from __future__ import annotations

from typing import Literal

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


class AnalysisReport(BaseModel):
    fit_summary: FitSummary
    jd_analysis: JDAnalysis
    candidate_evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_map: list[EvidenceMatch] = Field(default_factory=list)
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    ok: bool = True
    metadata: AnalysisMetadata
    fit_summary: FitSummary
    jd_analysis: JDAnalysis
    candidate_evidence: list[EvidenceItem]
    evidence_map: list[EvidenceMatch]
    follow_up_questions: list[FollowUpQuestion]
    warnings: list[str]
    markdown_report: str


class AnalyzeDemoRequest(BaseModel):
    cv_fixture: str
    jd_fixture: str
    mode: AnalysisMode = DEFAULT_MODE


class DemoOptionsResponse(BaseModel):
    cv_fixtures: list[DemoFixtureOption]
    jd_fixtures: list[DemoFixtureOption]
    default_cv_fixture: str
    default_jd_fixture: str
    modes: list[AnalysisMode] = Field(default_factory=lambda: ["safe", "stretch", "interview", "ideal"])
