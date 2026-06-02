from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import TimestampMixin, new_id


class ApplicationStatus(StrEnum):
    SAVED = "Saved"
    ANALYZING = "Analyzing"
    ANALYZED = "Analyzed"
    PACK_GENERATED = "Pack Generated"
    READY_TO_APPLY = "Ready to Apply"
    APPLYING = "Applying"
    NEEDS_USER_INPUT = "Needs User Input"
    APPLIED = "Applied"
    CONTACT_FOUND = "Contact Found"
    MESSAGE_DRAFTED = "Message Drafted"
    ARCHIVED = "Archived"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(80), default=ApplicationStatus.SAVED.value, nullable=False)
    fit_score: Mapped[int | None] = mapped_column(Integer)
    sponsorship_risk: Mapped[str | None] = mapped_column(String(200))
    recommendation: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(String(300))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_application_id: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    job: Mapped["Job"] = relationship(back_populates="application")
    packs: Mapped[list["ApplicationPack"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(back_populates="application")
    hermes_tasks: Mapped[list["HermesTask"]] = relationship(back_populates="application")
    approval_checkpoints: Mapped[list["ApprovalCheckpoint"]] = relationship(back_populates="application")
    status_events: Mapped[list["StatusEvent"]] = relationship(back_populates="application", cascade="all, delete-orphan")
