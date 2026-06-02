from sqlalchemy import select
from sqlalchemy.orm import Session

from haxjobs_api.features.profiles.models import ProfileFact, SavedAnswer, UserProfile
from haxjobs_api.features.profiles.schemas import ProfileFactCreate, SavedAnswerCreate, UserProfileCreate


def create_profile(session: Session, payload: UserProfileCreate) -> UserProfile:
    profile = UserProfile(**payload.model_dump())
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def list_profiles(session: Session) -> list[UserProfile]:
    return list(session.scalars(select(UserProfile).order_by(UserProfile.created_at.desc())).all())


def create_profile_fact(session: Session, profile_id: str, payload: ProfileFactCreate) -> ProfileFact | None:
    profile = session.get(UserProfile, profile_id)
    if profile is None:
        return None
    fact = ProfileFact(profile=profile, **payload.model_dump())
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact


def create_saved_answer(session: Session, profile_id: str, payload: SavedAnswerCreate) -> SavedAnswer | None:
    profile = session.get(UserProfile, profile_id)
    if profile is None:
        return None
    answer = SavedAnswer(profile=profile, **payload.model_dump())
    session.add(answer)
    session.commit()
    session.refresh(answer)
    return answer
