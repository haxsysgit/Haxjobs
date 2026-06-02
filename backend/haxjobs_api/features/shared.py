from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def new_id() -> str:
    """Create stable string IDs that work across SQLite now and Postgres later."""

    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ConfidenceLevel(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    WEAK = "weak"
    NEEDS_CONFIRMATION = "needs_confirmation"


class SensitivityLevel(StrEnum):
    NORMAL = "normal"
    REVIEW_BEFORE_USE = "review_before_use"
    LEGAL_SENSITIVE = "legal_sensitive"
    NEVER_AUTO_ANSWER = "never_auto_answer"
