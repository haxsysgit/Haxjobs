from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from haxjobs_api.features.profiles.models import ProfileFact, SavedAnswer, UserProfile


@dataclass(slots=True)
class ProfileImportResult:
    profile: UserProfile
    facts_imported: int
    saved_answers_imported: int


def import_profile_from_json(session: Session, path: str | Path) -> ProfileImportResult:
    """Import the ignored local HaxJobs profile JSON into database records.

    This is intentionally a local-development bridge. The future product flow is
    the HaxJobs profile/survey UI, but this lets us use Arinze's real fixture data
    while building the 0.1.x backend.
    """

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    user_payload = payload.get("user_profile", {})

    profile = UserProfile(
        full_name=user_payload.get("full_name") or user_payload.get("name") or "Unnamed Profile",
        email=user_payload.get("email"),
        phone=user_payload.get("phone"),
        location=user_payload.get("location"),
        linkedin_url=user_payload.get("linkedin_url"),
        github_url=user_payload.get("github_url"),
        portfolio_url=user_payload.get("portfolio_url"),
        work_authorization_summary=user_payload.get("work_authorization_summary"),
        requires_sponsorship=str(user_payload.get("requires_sponsorship")) if user_payload.get("requires_sponsorship") is not None else None,
        salary_preference=user_payload.get("salary_preference"),
        availability=user_payload.get("availability"),
        preferred_locations=user_payload.get("preferred_locations") or [],
        preferred_work_modes=user_payload.get("preferred_work_modes") or [],
        preferred_roles=user_payload.get("preferred_roles") or [],
    )
    session.add(profile)
    session.flush()

    facts_imported = 0
    for fact_payload in payload.get("confirmed_profile_facts", []):
        session.add(
            ProfileFact(
                profile=profile,
                category=fact_payload.get("category") or "general",
                claim=fact_payload.get("claim") or fact_payload.get("text") or "",
                safe_wording=fact_payload.get("safe_wording"),
                avoid_wording=fact_payload.get("avoid_wording"),
                evidence_source=fact_payload.get("evidence_source"),
                confidence=fact_payload.get("confidence") or "confirmed",
            )
        )
        facts_imported += 1

    saved_answers_imported = 0
    for answer_payload in payload.get("saved_answers", []):
        session.add(
            SavedAnswer(
                profile=profile,
                question_key=answer_payload.get("question_key") or "unknown",
                question_text=answer_payload.get("question_text") or answer_payload.get("question_key") or "Unknown question",
                answer=answer_payload.get("answer"),
                sensitivity=answer_payload.get("sensitivity") or "review_before_use",
            )
        )
        saved_answers_imported += 1

    session.commit()
    session.refresh(profile)
    return ProfileImportResult(profile=profile, facts_imported=facts_imported, saved_answers_imported=saved_answers_imported)
