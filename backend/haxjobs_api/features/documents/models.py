from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import new_id, utc_now
from sqlalchemy import DateTime
from datetime import datetime


class DocumentType(StrEnum):
    TAILORED_CV = "tailored_cv"
    COVER_LETTER = "cover_letter"
    APPLICATION_QUESTIONS = "application_questions"
    COMBINED_PACK = "combined_pack"
    FIT_REPORT = "fit_report"
    NOTES = "notes"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_pack_id: Mapped[str] = mapped_column(ForeignKey("application_packs.id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[str] = mapped_column(String(30), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1", nullable=False)
    is_submitted_version: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    pack: Mapped["ApplicationPack"] = relationship(back_populates="documents")
