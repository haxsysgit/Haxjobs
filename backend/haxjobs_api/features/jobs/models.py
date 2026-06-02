from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import TimestampMixin, new_id, utc_now


class SourcePlatform(StrEnum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    REED = "reed"
    COMPANY_SITE = "company_site"
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    MANUAL = "manual"
    OTHER = "other"


class JobStatus(StrEnum):
    SAVED = "saved"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    location: Mapped[str | None] = mapped_column(String(250))
    source_platform: Mapped[str] = mapped_column(String(80), default=SourcePlatform.MANUAL.value, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    job_description: Mapped[str | None] = mapped_column(Text)
    salary_text: Mapped[str | None] = mapped_column(String(250))
    work_mode: Mapped[str | None] = mapped_column(String(80))
    seniority: Mapped[str | None] = mapped_column(String(100))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    sponsorship_signal: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(80), default=JobStatus.SAVED.value, nullable=False)

    snapshots: Mapped[list[JobSourceSnapshot]] = relationship(back_populates="job", cascade="all, delete-orphan")
    application: Mapped["Application | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    hermes_tasks: Mapped[list["HermesTask"]] = relationship(back_populates="job")


class JobSourceSnapshot(Base):
    __tablename__ = "job_source_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(300))
    source_platform: Mapped[str] = mapped_column(String(80), default=SourcePlatform.MANUAL.value, nullable=False)
    visible_text: Mapped[str | None] = mapped_column(Text)
    selected_text: Mapped[str | None] = mapped_column(Text)
    html_snapshot_path: Mapped[str | None] = mapped_column(String(1000))
    screenshot_path: Mapped[str | None] = mapped_column(String(1000))
    user_note: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[Job | None] = relationship(back_populates="snapshots")
