from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import TimestampMixin, new_id, utc_now


class TaskType(StrEnum):
    ANALYZE_JOB = "analyze_job"
    GENERATE_PACK = "generate_pack"
    FIND_CONTACTS = "find_contacts"
    DRAFT_OUTREACH = "draft_outreach"
    APPLY_ASSIST = "apply_assist"
    RANK_SAVED_JOBS = "rank_saved_jobs"
    REFRESH_APPLICATION_STATUS = "refresh_application_status"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_USER_INPUT = "needs_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HermesTask(TimestampMixin, Base):
    __tablename__ = "hermes_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default=TaskStatus.PENDING.value, nullable=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"))
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("user_profiles.id", ondelete="SET NULL"))
    pack_id: Mapped[str | None] = mapped_column(ForeignKey("application_packs.id", ondelete="SET NULL"))
    input_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_payload_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped["Job | None"] = relationship(back_populates="hermes_tasks")
    application: Mapped["Application | None"] = relationship(back_populates="hermes_tasks")
    approval_checkpoints: Mapped[list["ApprovalCheckpoint"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class ApprovalCheckpoint(TimestampMixin, Base):
    __tablename__ = "approval_checkpoints"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("hermes_tasks.id", ondelete="SET NULL"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"))
    checkpoint_type: Mapped[str] = mapped_column(String(100), default="approval_required", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    question_key: Mapped[str | None] = mapped_column(String(150))
    sensitivity: Mapped[str | None] = mapped_column(String(80))
    approved: Mapped[bool | None] = mapped_column(default=None)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    task: Mapped[HermesTask | None] = relationship(back_populates="approval_checkpoints")
    application: Mapped["Application | None"] = relationship(back_populates="approval_checkpoints")


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    application: Mapped["Application | None"] = relationship(back_populates="status_events")
