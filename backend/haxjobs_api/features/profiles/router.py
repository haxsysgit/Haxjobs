from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from haxjobs_api.database import get_db_session
from haxjobs_api.features.profiles.repository import create_profile, create_profile_fact, create_saved_answer, list_profiles
from haxjobs_api.features.profiles.schemas import (
    ProfileFactCreate,
    ProfileFactRead,
    SavedAnswerCreate,
    SavedAnswerRead,
    UserProfileCreate,
    UserProfileRead,
)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def add_profile(payload: UserProfileCreate, session: Session = Depends(get_db_session)):
    return create_profile(session, payload)


@router.get("", response_model=list[UserProfileRead])
def read_profiles(session: Session = Depends(get_db_session)):
    return list_profiles(session)


@router.post("/{profile_id}/facts", response_model=ProfileFactRead, status_code=status.HTTP_201_CREATED)
def add_profile_fact(profile_id: str, payload: ProfileFactCreate, session: Session = Depends(get_db_session)):
    fact = create_profile_fact(session, profile_id, payload)
    if fact is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return fact


@router.post("/{profile_id}/answers", response_model=SavedAnswerRead, status_code=status.HTTP_201_CREATED)
def add_saved_answer(profile_id: str, payload: SavedAnswerCreate, session: Session = Depends(get_db_session)):
    answer = create_saved_answer(session, profile_id, payload)
    if answer is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return answer
