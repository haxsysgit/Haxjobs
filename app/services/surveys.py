from __future__ import annotations

from app.models.analysis import EvidenceMatch, FollowUpQuestion, SurveyChoice, SurveyQuestion


def build_survey_questions(
    evidence_map: list[EvidenceMatch],
    follow_up_questions: list[FollowUpQuestion],
) -> list[SurveyQuestion]:
    question_lookup = {question.requirement_id: question for question in follow_up_questions}
    survey_questions: list[SurveyQuestion] = []
    for match in evidence_map:
        question = question_lookup.get(match.requirement_id)
        if question is None:
            continue
        survey_questions.append(
            SurveyQuestion(
                question_id=match.requirement_id,
                requirement_id=match.requirement_id,
                requirement_text=match.requirement_text,
                prompt=question.question,
                helper_text=_helper_text(match, question),
                priority=question.priority,
                choices=_choices_for_match(match),
            )
        )
    return survey_questions


def compose_follow_up_answer(choice_label: str, notes: str) -> str:
    normalized_notes = notes.strip()
    if normalized_notes:
        return f"{choice_label}. {normalized_notes}".strip()
    return choice_label.strip()


def _helper_text(match: EvidenceMatch, question: FollowUpQuestion) -> str:
    if match.match_label == "Gap":
        return "Pick the closest true option first, then add a short note in your own words."
    if match.claim_label == "Needs User Confirmation":
        return "Choose the option that feels true even if your English is short. The note is optional."
    return question.reason


def _choices_for_match(match: EvidenceMatch) -> list[SurveyChoice]:
    if match.match_label == "Gap":
        return [
            SurveyChoice(
                id="no-experience",
                label="I have not done this yet",
                description="There is no real example today.",
            ),
            SurveyChoice(
                id="learning-only",
                label="I learned or practiced this",
                description="Coursework, self-study, or experiments only.",
            ),
            SurveyChoice(
                id="related-experience",
                label="I did something related",
                description="A nearby skill or responsibility, not the exact same thing.",
            ),
            SurveyChoice(
                id="can-explain",
                label="I have an honest example",
                description="I can explain one real example if asked.",
            ),
        ]
    if match.match_label == "Weak Match":
        return [
            SurveyChoice(
                id="direct-example",
                label="I did this directly",
                description="I have a real project or work example.",
            ),
            SurveyChoice(
                id="related-example",
                label="I did something similar",
                description="The experience is close, but not exact.",
            ),
            SurveyChoice(
                id="project-only",
                label="Only in projects or study",
                description="Not in paid work, but I practiced it.",
            ),
            SurveyChoice(
                id="not-ready",
                label="I am not ready to claim this",
                description="Better to keep this as a gap for now.",
            ),
        ]
    return [
        SurveyChoice(
            id="strong-proof",
            label="I have strong proof",
            description="I can defend this clearly in interview.",
        ),
        SurveyChoice(
            id="partial-proof",
            label="I have some proof",
            description="The example is real but still incomplete.",
        ),
        SurveyChoice(
            id="transferable-proof",
            label="My experience is transferable",
            description="The skill is nearby, not a direct one-to-one match.",
        ),
        SurveyChoice(
            id="skip-claim",
            label="Do not use this strongly",
            description="Keep the wording soft or leave it out.",
        ),
    ]

