from __future__ import annotations

import json

from app.models.analysis import AnalysisMetadata, AnalysisReport, AnalyzeResponse


def generate_markdown_report(report: AnalysisReport, metadata: AnalysisMetadata | None = None) -> str:
    lines: list[str] = []
    if metadata is not None:
        lines.append("# Analysis Metadata")
        lines.append(f"- Mode: {metadata.mode}")
        lines.append(f"- Source: {metadata.source}")
        lines.append(f"- CV Label: {metadata.cv_label}")
        lines.append(f"- JD Label: {metadata.jd_label}")
        lines.append("")
    lines.append("# Fit Summary")
    lines.append(
        f"- Score: {report.fit_summary.score}/100 ({report.fit_summary.label})"
    )
    lines.append(
        f"- Coverage: {report.fit_summary.matched_requirements}/{report.fit_summary.total_requirements} extracted requirements"
    )
    lines.append(f"- Summary: {report.fit_summary.summary}")
    lines.append("")
    lines.append("# JD Analysis")
    lines.append(f"- Role Title: {report.jd_analysis.role_title}")
    lines.append(
        f"- Required Skill Signals: {', '.join(report.jd_analysis.required_skills) or 'None extracted'}"
    )
    lines.append(
        f"- Desirable Skill Signals: {', '.join(report.jd_analysis.desirable_skills) or 'None extracted'}"
    )
    lines.append(
        f"- Recruiter Concerns: {', '.join(report.jd_analysis.recruiter_concerns) or 'None extracted'}"
    )
    lines.append("")
    lines.append("# Candidate Evidence")
    for item in report.candidate_evidence:
        lines.append(f"- [{item.source_section}] {item.evidence}")
    lines.append("")
    lines.append("# Evidence Map")
    lines.append("| Requirement | Match | Claim | Evidence |")
    lines.append("| --- | --- | --- | --- |")
    for match in report.evidence_map:
        evidence = "; ".join(match.supporting_evidence) or "No direct evidence found"
        lines.append(
            f"| {_escape_pipes(match.requirement_text)} | {match.match_label} | {match.claim_label} | {_escape_pipes(evidence)} |"
        )
    lines.append("")
    lines.append("# Gaps and Warnings")
    for warning in report.warnings:
        lines.append(f"- {warning}")
    for match in report.evidence_map:
        if match.risk_warning:
            lines.append(f"- {match.requirement_text}: {match.risk_warning}")
    lines.append("")
    lines.append("# Follow-up Questions")
    for question in report.follow_up_questions:
        lines.append(f"- ({question.priority}) {question.question}")
    return "\n".join(lines).strip()


def response_from_report(report: AnalysisReport, metadata: AnalysisMetadata) -> AnalyzeResponse:
    return AnalyzeResponse(
        metadata=metadata,
        fit_summary=report.fit_summary,
        jd_analysis=report.jd_analysis,
        candidate_evidence=report.candidate_evidence,
        evidence_map=report.evidence_map,
        follow_up_questions=report.follow_up_questions,
        warnings=report.warnings,
        markdown_report=generate_markdown_report(report, metadata=metadata),
    )


def json_from_response(response: AnalyzeResponse) -> str:
    return json.dumps(response.model_dump(mode="json"), indent=2)


def _escape_pipes(value: str) -> str:
    return value.replace("|", "\\|")
