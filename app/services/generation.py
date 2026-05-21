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
CV_HIGHLIGHT_LIMIT = 7
CV_SKILL_LIMIT = 12
INTERVIEW_TRIGGER_TERMS = (
    "interview",
    "walk through",
    "walkthrough",
    "case study",
    "portfolio",
    "examples of systems",
    "examples of work",
    "video",
    "loom",
    "presentation",
)


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
        "internal_guardrails": {
            "evidence_map": [match.model_dump(mode="json") for match in analysis.evidence_map],
            "warnings": analysis.warnings,
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
                "# Aspirational Candidate Profile",
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
            f"Target role: {analysis.jd_analysis.role_title}",
            "",
            "> Format target: concise ATS-friendly CV, normally 2 pages and never more than 3 pages unless the role is academic, federal, or explicitly requests a long CV.",
            "",
            "## Summary",
        ]
    )
    summary_points = _summary_points(analysis, included_matches, unresolved_matches, answers)
    for point in summary_points:
        lines.append(f"- {point}")
    lines.extend(["", "## Role-Fit Highlights"])
    if included_matches:
        for match in included_matches[:CV_HIGHLIGHT_LIMIT]:
            lines.append(f"- {match.suggested_safe_wording}")
            answer = answers.get(match.requirement_id)
            if _has_resolved_answer(answer):
                lines.append(f"- {answer.answer}")
            confirmation = claim_confirmations.get(match.requirement_id)
            if _has_confirmed_claim(confirmation) and confirmation.notes:
                lines.append(f"- {confirmation.notes}")
    else:
        lines.append("- Position the strongest reusable profile themes against this JD and keep the wording concrete.")
    lines.extend(["", "## Skills"])
    skill_signals = _skill_signals(analysis)
    if skill_signals:
        lines.append(", ".join(skill_signals))
    else:
        lines.append("Role-relevant skills should be selected from the candidate profile and this job description.")
    if unresolved_matches:
        lines.extend(["", "## Interview-Ready Positioning Notes"])
        for line in _positioning_notes(unresolved_matches):
            lines.append(f"- {line}")
    if user_notes and user_notes.strip():
        lines.extend(["", "## User Direction", f"- {user_notes.strip()}"])
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
                f"I am applying for the {analysis.jd_analysis.role_title} role because the work maps closely to the systems I have been building: practical software, operational workflows, and role-specific problem solving.",
                f"My strongest fit is around {analysis.fit_summary.summary}",
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
            "Where the role asks for adjacent experience, I would bring a practical learning mindset and connect it to the closest systems I have already delivered."
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
    requested = _jd_requests_interview_artifact(analysis)
    lines = ["# Application Notes", ""]
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
        lines.append("- Lead with the strongest reusable profile themes that overlap with this role.")
    lines.extend(["", "## Smart Positioning"])
    careful = [
        match
        for match in analysis.evidence_map
        if match.claim_label in {"Inferred", "Stretch Wording", "Needs User Confirmation"}
    ]
    if careful:
        for match in _sorted_matches(careful)[:5]:
            answer = answers.get(match.requirement_id)
            line = f"{match.requirement_text}: {_soft_positioning(match)}"
            if _has_resolved_answer(answer):
                line = f"{line} Example to use: {answer.answer}"
            confirmation = claim_confirmations.get(match.requirement_id)
            if _has_confirmed_claim(confirmation) and confirmation.notes:
                line = f"{line} Context: {confirmation.notes}"
            lines.append(f"- {line}")
    else:
        lines.append("- No special positioning notes were needed from this pass.")
    if requested:
        lines.extend(["", "## Optional Video Or Walkthrough"])
        lines.append("- This JD asks for examples, a walkthrough, portfolio material, or interview-style explanation. Prepare a short project story only for that request.")
    else:
        lines.extend(["", "## Optional Extras"])
        lines.append("- Do not create a Loom/video by default. Prepare one only when the JD asks for it or the application specifically benefits from examples of systems built.")
    if analysis.follow_up_questions:
        lines.extend(["", "## Profile Questions That Would Improve Future Packs"])
        for question in analysis.follow_up_questions[:5]:
            answer = answers.get(question.requirement_id)
            if _has_resolved_answer(answer):
                lines.append(f"- {answer.answer}")
            elif not (answer and answer.skipped):
                lines.append(f"- {question.question}")
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
            "Show the strongest plausible role profile without presenting it as the candidate's submitted CV.",
            f"Keep the sample concise and focused on the highest-signal {analysis.jd_analysis.role_title} requirements.",
        ]
    if not included_matches:
        return [
            "Lead with the candidate's strongest reusable profile themes and adapt them to this role.",
            "Use profile-informed, plausible wording instead of exposing internal match mechanics.",
        ]
    top_categories = Counter(match.section for match in included_matches[:4])
    strongest_section = top_categories.most_common(1)[0][0] if top_categories else "the profile"
    answer_total = sum(1 for answer in answers.values() if _has_resolved_answer(answer))
    points = [
        analysis.fit_summary.summary,
        f"Emphasize the strongest {strongest_section.lower()} overlap in the first screen of the CV.",
    ]
    if answer_total:
        points.append(f"Fold in {answer_total} user-provided detail(s) where they make the role fit sharper.")
    if unresolved_matches:
        points.append("Use transferable wording for adjacent requirements without wasting CV space on gap explanations.")
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


def _skill_signals(analysis: AnalyzeResponse) -> list[str]:
    seen: set[str] = set()
    skills: list[str] = []
    for skill in [*analysis.jd_analysis.required_skills, *analysis.jd_analysis.desirable_skills]:
        normalized = skill.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            skills.append(normalized)
        if len(skills) >= CV_SKILL_LIMIT:
            break
    return skills


def _positioning_notes(unresolved_matches: list[EvidenceMatch]) -> list[str]:
    notes: list[str] = []
    for match in unresolved_matches[:4]:
        notes.append(_soft_positioning(match))
    return notes or ["Keep the final CV focused on the strongest role-relevant profile signals."]


def _soft_positioning(match: EvidenceMatch) -> str:
    if match.match_label == "Gap":
        return f"If asked about {match.requirement_text.lower()}, position it as a learning area or adjacent exposure rather than a core claim."
    return match.suggested_safe_wording


def _jd_requests_interview_artifact(analysis: AnalyzeResponse) -> bool:
    jd_parts = [
        analysis.jd_analysis.role_title,
        *analysis.jd_analysis.section_titles,
        *analysis.jd_analysis.recruiter_concerns,
        *(requirement.text for requirement in analysis.jd_analysis.requirements),
    ]
    jd_text = " ".join(jd_parts).lower()
    return any(term in jd_text for term in INTERVIEW_TRIGGER_TERMS)


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
