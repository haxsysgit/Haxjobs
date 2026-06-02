from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import ConfidenceLevel, SensitivityLevel, TimestampMixin, new_id


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    work_authorization_summary: Mapped[str | None] = mapped_column(Text)
    requires_sponsorship: Mapped[str | None] = mapped_column(String(200))
    salary_preference: Mapped[str | None] = mapped_column(Text)
    availability: Mapped[str | None] = mapped_column(String(200))
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_work_modes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    facts: Mapped[list[ProfileFact]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    saved_answers: Mapped[list[SavedAnswer]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class ProfileFact(TimestampMixin, Base):
    __tablename__ = "profile_facts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    safe_wording: Mapped[str | None] = mapped_column(Text)
    avoid_wording: Mapped[str | None] = mapped_column(Text)
    evidence_source: Mapped[str | None] = mapped_column(String(300))
    confidence: Mapped[str] = mapped_column(String(40), default=ConfidenceLevel.NEEDS_CONFIRMATION.value, nullable=False)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[UserProfile] = relationship(back_populates="facts")


class SavedAnswer(TimestampMixin, Base):
    __tablename__ = "saved_answers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    question_key: Mapped[str] = mapped_column(String(150), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(String(40), default=SensitivityLevel.REVIEW_BEFORE_USE.value, nullable=False)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[UserProfile] = relationship(back_populates="saved_answers")
