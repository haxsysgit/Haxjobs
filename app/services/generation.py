from __future__ import annotations

from collections import Counter

from app.models.analysis import (
    AnalyzeResponse,
    EvidenceMatch,
    FollowUpAnswer,
    GenerateApplicationPackResponse,
    GenerationMetadata,
    UserClaimConfirmation,
)

MATCH_RANK = {
    "Strong Match": 0,
    "Partial Match": 1,
    "Transferable Match": 2,
    "Weak Match": 3,
    "Gap": 4,
}
ALWAYS_ALLOWED_CLAIMS = {"Confirmed"}
STRETCH_ALLOWED_CLAIMS = {"Confirmed", "Inferred", "Stretch Wording"}


def generate_application_pack(
    analysis: AnalyzeResponse,
    follow_up_answers: list[FollowUpAnswer] | None = None,
    user_claim_confirmations: list[UserClaimConfirmation] | None = None,
    user_notes: str | None = None,
) -> GenerateApplicationPackResponse:
    answers = _build_answer_lookup(follow_up_answers or [])
    claim_confirmations = _build_confirmation_lookup(user_claim_confirmations or [])
    included_matches = _included_matches(analysis, answers, claim_confirmations)
    unresolved_matches = _unresolved_matches(analysis, answers, claim_confirmations)
    answer_count = sum(1 for answer in answers.values() if answer.answer and not answer.skipped)
    unanswered_count = sum(
        1
        for question in analysis.follow_up_questions
        if question.priority == "high"
        and not _is_resolved_requirement(
            answers.get(question.requirement_id),
            claim_confirmations.get(question.requirement_id),
        )
    )
    tailored_cv_markdown = _build_tailored_cv(
        analysis=analysis,
        included_matches=included_matches,
        unresolved_matches=unresolved_matches,
        answers=answers,
        claim_confirmations=claim_confirmations,
        user_notes=user_notes,
    )
    cover_letter_markdown = _build_cover_letter(
        analysis=analysis,
        included_matches=included_matches,
        unresolved_matches=unresolved_matches,
        answers=answers,
        claim_confirmations=claim_confirmations,
        user_notes=user_notes,
    )
    interview_notes_markdown = _build_interview_notes(
        analysis=analysis,
        included_matches=included_matches,
        unresolved_matches=unresolved_matches,
        answers=answers,
        claim_confirmations=claim_confirmations,
        user_notes=user_notes,
    )
    metadata = GenerationMetadata(
        mode=analysis.metadata.mode,
        role_title=analysis.jd_analysis.role_title,
        source=analysis.metadata.source,
        aspirational=analysis.metadata.mode == "ideal",
        follow_up_answer_count=answer_count,
        unanswered_follow_up_count=unanswered_count,
        generated_documents=[
            "tailored_cv_markdown",
            "cover_letter_markdown",
            "interview_notes_markdown",
            "evidence_map_json",
            "application_pack_json",
        ],
    )
    application_pack_json = {
        "metadata": metadata.model_dump(mode="json"),
        "analysis_metadata": analysis.metadata.model_dump(mode="json"),
        "fit_summary": analysis.fit_summary.model_dump(mode="json"),
        "documents": {
            "tailored_cv_markdown": tailored_cv_markdown,
            "cover_letter_markdown": cover_letter_markdown,
            "interview_notes_markdown": interview_notes_markdown,
        },
        "evidence_map": [match.model_dump(mode="json") for match in analysis.evidence_map],
        "follow_up_answers": [
            answer.model_dump(mode="json")
            for answer in sorted(answers.values(), key=lambda item: item.requirement_id)
        ],
        "user_claim_confirmations": [
            confirmation.model_dump(mode="json")
            for confirmation in sorted(
                claim_confirmations.values(), key=lambda item: item.requirement_id
            )
        ],
        "warnings": analysis.warnings,
        "user_notes": (user_notes or "").strip() or None,
    }
    return GenerateApplicationPackResponse(
        metadata=metadata,
        tailored_cv_markdown=tailored_cv_markdown,
        cover_letter_markdown=cover_letter_markdown,
        interview_notes_markdown=interview_notes_markdown,
        evidence_map_json=analysis.evidence_map,
        application_pack_json=application_pack_json,
    )


def _build_answer_lookup(follow_up_answers: list[FollowUpAnswer]) -> dict[str, FollowUpAnswer]:
    answers: dict[str, FollowUpAnswer] = {}
    for answer in follow_up_answers:
        normalized = answer.answer.strip()
        answers[answer.requirement_id] = FollowUpAnswer(
            requirement_id=answer.requirement_id,
            answer=normalized,
            skipped=answer.skipped,
        )
    return answers


def _build_confirmation_lookup(
    confirmations: list[UserClaimConfirmation],
) -> dict[str, UserClaimConfirmation]:
    lookup: dict[str, UserClaimConfirmation] = {}
    for confirmation in confirmations:
        lookup[confirmation.requirement_id] = UserClaimConfirmation(
            requirement_id=confirmation.requirement_id,
            status=confirmation.status,
            notes=confirmation.notes.strip(),
        )
    return lookup


def _included_matches(
    analysis: AnalyzeResponse,
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
) -> list[EvidenceMatch]:
    if analysis.metadata.mode == "ideal":
        return _sorted_matches(analysis.evidence_map)
    allowed_claims = (
        ALWAYS_ALLOWED_CLAIMS
        if analysis.metadata.mode == "safe"
        else STRETCH_ALLOWED_CLAIMS
    )
    included: list[EvidenceMatch] = []
    for match in analysis.evidence_map:
        answer = answers.get(match.requirement_id)
        confirmation = claim_confirmations.get(match.requirement_id)
        if match.claim_label in allowed_claims or _is_resolved_requirement(answer, confirmation):
            included.append(match)
    return _sorted_matches(included)


def _unresolved_matches(
    analysis: AnalyzeResponse,
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
) -> list[EvidenceMatch]:
    unresolved: list[EvidenceMatch] = []
    included_ids = {
        match.requirement_id
        for match in _included_matches(analysis, answers, claim_confirmations)
    }
    for match in analysis.evidence_map:
        if match.requirement_id not in included_ids or match.match_label == "Gap":
            unresolved.append(match)
    return _sorted_matches(unresolved)


def _sorted_matches(matches: list[EvidenceMatch]) -> list[EvidenceMatch]:
    return sorted(
        matches,
        key=lambda match: (
            0 if match.importance == "required" else 1,
            MATCH_RANK[match.match_label],
            match.requirement_text.lower(),
        ),
    )


def _has_resolved_answer(answer: FollowUpAnswer | None) -> bool:
    return bool(answer and answer.answer.strip() and not answer.skipped)


def _has_confirmed_claim(confirmation: UserClaimConfirmation | None) -> bool:
    return bool(confirmation and confirmation.status == "confirmed")


def _is_resolved_requirement(
    answer: FollowUpAnswer | None,
    confirmation: UserClaimConfirmation | None,
) -> bool:
    return _has_resolved_answer(answer) or _has_confirmed_claim(confirmation)


def _build_tailored_cv(
    analysis: AnalyzeResponse,
    included_matches: list[EvidenceMatch],
    unresolved_matches: list[EvidenceMatch],
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
    user_notes: str | None,
) -> str:
    lines: list[str] = []
    if analysis.metadata.mode == "ideal":
        lines.extend(
            [
                "# Aspirational Tailored CV Sample",
                "",
                "> Ideal mode: this sample shows the shape of the candidate the JD appears to want.",
                "> It is not a claim that the current candidate already has this full background.",
                "",
            ]
        )
    else:
        lines.extend(["# Tailored CV Draft", ""])
    lines.extend(
        [
            f"## Target Role",
            analysis.jd_analysis.role_title,
            "",
            "## Professional Summary",
        ]
    )
    summary_points = _summary_points(analysis, included_matches, unresolved_matches, answers)
    for point in summary_points:
        lines.append(f"- {point}")
    lines.extend(["", "## Evidence-Aligned Highlights"])
    if included_matches:
        for match in included_matches[:6]:
            lines.append(f"- {match.suggested_safe_wording}")
            answer = answers.get(match.requirement_id)
            if _has_resolved_answer(answer):
                lines.append(f"- User-confirmed example for {match.requirement_text}: {answer.answer}")
            confirmation = claim_confirmations.get(match.requirement_id)
            if _has_confirmed_claim(confirmation) and confirmation.notes:
                lines.append(
                    f"- Claim confirmation note for {match.requirement_text}: {confirmation.notes}"
                )
    else:
        lines.append("- Keep the CV conservative. The current evidence map does not support stronger tailored claims yet.")
    lines.extend(["", "## Skills Alignment"])
    required = ", ".join(analysis.jd_analysis.required_skills) or "No clear required skill signals extracted"
    desirable = ", ".join(analysis.jd_analysis.desirable_skills) or "No clear nice-to-have skills extracted"
    lines.append(f"- Required signals to foreground: {required}")
    lines.append(f"- Nice-to-have signals to position carefully: {desirable}")
    lines.extend(["", "## Gaps To Handle Carefully"])
    gap_lines = _gap_lines(unresolved_matches)
    for line in gap_lines:
        lines.append(f"- {line}")
    if user_notes and user_notes.strip():
        lines.extend(["", "## User Notes To Respect", f"- {user_notes.strip()}"])
    return "\n".join(lines).strip()


def _build_cover_letter(
    analysis: AnalyzeResponse,
    included_matches: list[EvidenceMatch],
    unresolved_matches: list[EvidenceMatch],
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
    user_notes: str | None,
) -> str:
    greeting = "Dear Hiring Team,"
    lines = ["# Cover Letter Draft", "", greeting, ""]
    if analysis.metadata.mode == "ideal":
        lines.extend(
            [
                "This is an aspirational sample cover letter based on the job description rather than a statement of the current candidate's exact background.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"I am applying for the {analysis.jd_analysis.role_title} role with an evidence-first approach to the match.",
                f"The current fit map scores this role as {analysis.fit_summary.label.lower()} at {analysis.fit_summary.score}/100, with the strongest support coming from documented backend, API, and workflow evidence.",
                "",
            ]
        )
    highlight_lines = _letter_highlights(
        included_matches,
        answers,
        claim_confirmations,
        aspirational=analysis.metadata.mode == "ideal",
    )
    if highlight_lines:
        lines.extend(highlight_lines)
        lines.append("")
    if unresolved_matches:
        lines.append(
            "I would position the remaining weaker areas honestly, using transferable examples where they exist and treating direct gaps as gaps rather than overstated experience."
        )
        lines.append("")
    if user_notes and user_notes.strip():
        lines.append(f"Additional context to preserve in the final version: {user_notes.strip()}")
        lines.append("")
    lines.extend(["Thank you for your time and consideration.", "", "Sincerely,", "[Candidate Name]"])
    return "\n".join(lines).strip()


def _build_interview_notes(
    analysis: AnalyzeResponse,
    included_matches: list[EvidenceMatch],
    unresolved_matches: list[EvidenceMatch],
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
    user_notes: str | None,
) -> str:
    lines = ["# Interview Notes", ""]
    if analysis.metadata.mode == "ideal":
        lines.extend(
            [
                "> Ideal mode: use these notes as a benchmark for what the role values, not as a script for unsupported claims.",
                "",
            ]
        )
    lines.extend(["## Strongest Talking Points"])
    for match in included_matches[:5]:
        lines.append(
            f"- {match.requirement_text}: "
            f"{_talking_point(match, answers.get(match.requirement_id), claim_confirmations.get(match.requirement_id))}"
        )
    if not included_matches:
        lines.append("- No safe talking points were generated from the current evidence set.")
    lines.extend(["", "## Claims To Defend Carefully"])
    careful = [
        match
        for match in analysis.evidence_map
        if match.claim_label in {"Inferred", "Stretch Wording", "Needs User Confirmation"}
    ]
    if careful:
        for match in _sorted_matches(careful)[:5]:
            answer = answers.get(match.requirement_id)
            line = f"{match.requirement_text}: {match.risk_warning or match.suggested_safe_wording}"
            if _has_resolved_answer(answer):
                line = f"{line} User-confirmed example: {answer.answer}"
            confirmation = claim_confirmations.get(match.requirement_id)
            if _has_confirmed_claim(confirmation) and confirmation.notes:
                line = f"{line} Claim confirmation: {confirmation.notes}"
            lines.append(f"- {line}")
    else:
        lines.append("- No defensive claim handling notes were needed from this pass.")
    lines.extend(["", "## Follow-up Questions"])
    for question in analysis.follow_up_questions:
        answer = answers.get(question.requirement_id)
        status = _question_status(answer)
        lines.append(f"- [{question.priority}] {question.question}")
        lines.append(f"- Status: {status}")
        if _has_resolved_answer(answer):
            lines.append(f"- Answer: {answer.answer}")
        elif answer and answer.skipped:
            lines.append("- Answer: Skipped for now.")
    if not analysis.follow_up_questions:
        lines.append("- No follow-up questions were generated.")
    lines.extend(["", "## Gaps To Address Honestly"])
    for line in _gap_lines(unresolved_matches):
        lines.append(f"- {line}")
    if user_notes and user_notes.strip():
        lines.extend(["", "## User Notes", f"- {user_notes.strip()}"])
    return "\n".join(lines).strip()


def _summary_points(
    analysis: AnalyzeResponse,
    included_matches: list[EvidenceMatch],
    unresolved_matches: list[EvidenceMatch],
    answers: dict[str, FollowUpAnswer],
) -> list[str]:
    if analysis.metadata.mode == "ideal":
        return [
            f"Shape the document around the {analysis.jd_analysis.role_title} brief and keep it clearly labeled as aspirational.",
            "Use the evidence map as a boundary for what is real versus what is only a target profile.",
            f"Call out {len(unresolved_matches)} weaker or missing areas separately so they do not read as confirmed experience.",
        ]
    if not included_matches:
        return [
            "Keep the summary conservative until stronger evidence is confirmed.",
            "Use the evidence map to decide which JD requirements should appear as strengths, stretch wording, or explicit gaps.",
        ]
    top_categories = Counter(match.section for match in included_matches[:4])
    strongest_section = top_categories.most_common(1)[0][0] if top_categories else "the evidence map"
    answer_total = sum(1 for answer in answers.values() if _has_resolved_answer(answer))
    points = [
        f"Lead with the defensible fit summary: {analysis.fit_summary.summary}",
        f"Anchor the summary in the strongest current evidence from {strongest_section.lower()}.",
    ]
    if answer_total:
        points.append(f"Fold in {answer_total} user-confirmed follow-up example(s) only where they tighten a weak or partial claim.")
    if unresolved_matches:
        points.append(f"Surface {len(unresolved_matches)} unresolved or gap item(s) separately instead of blending them into the core pitch.")
    return points


def _letter_highlights(
    included_matches: list[EvidenceMatch],
    answers: dict[str, FollowUpAnswer],
    claim_confirmations: dict[str, UserClaimConfirmation],
    aspirational: bool,
) -> list[str]:
    lines: list[str] = []
    if not included_matches:
        return lines
    leading = included_matches[:3]
    first_sentence = "The clearest alignment points are"
    if aspirational:
        first_sentence = "An ideal profile for this role would emphasize"
    lines.append(
        f"{first_sentence} "
        + ", ".join(match.requirement_text.lower() for match in leading[:-1])
        + (f", and {leading[-1].requirement_text.lower()}." if len(leading) > 1 else f" {leading[0].requirement_text.lower()}.")
    )
    for match in leading:
        answer = answers.get(match.requirement_id)
        confirmation = claim_confirmations.get(match.requirement_id)
        if _has_resolved_answer(answer):
            lines.append(
                f"I can support {match.requirement_text.lower()} with a user-confirmed example: {answer.answer}"
            )
        elif _has_confirmed_claim(confirmation) and confirmation.notes:
            lines.append(
                f"{match.requirement_text}: user-confirmed claim note to preserve - {confirmation.notes}"
            )
        else:
            lines.append(match.suggested_safe_wording)
    return lines


def _gap_lines(unresolved_matches: list[EvidenceMatch]) -> list[str]:
    gaps = [match for match in unresolved_matches if match.match_label == "Gap"]
    if gaps:
        return [
            f"{match.requirement_text}: {match.risk_warning or 'Treat as a direct gap until real evidence exists.'}"
            for match in gaps[:4]
        ]
    if unresolved_matches:
        return [
            f"{match.requirement_text}: keep the wording careful because the current evidence stays below a direct match."
            for match in unresolved_matches[:4]
        ]
    return ["No direct gaps were surfaced in this deterministic pass."]


def _talking_point(
    match: EvidenceMatch,
    answer: FollowUpAnswer | None,
    confirmation: UserClaimConfirmation | None,
) -> str:
    if _has_resolved_answer(answer):
        return f"{match.suggested_safe_wording} User-confirmed follow-up: {answer.answer}"
    if _has_confirmed_claim(confirmation) and confirmation.notes:
        return f"{match.suggested_safe_wording} Claim confirmation note: {confirmation.notes}"
    return match.suggested_safe_wording


def _question_status(answer: FollowUpAnswer | None) -> str:
    if _has_resolved_answer(answer):
        return "Answered"
    if answer and answer.skipped:
        return "Skipped"
    return "Pending"
