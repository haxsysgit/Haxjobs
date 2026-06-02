from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import TimestampMixin, new_id


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str | None] = mapped_column(String(250))
    company: Mapped[str | None] = mapped_column(String(200))
    platform: Mapped[str | None] = mapped_column(String(100))
    profile_url: Mapped[str | None] = mapped_column(String(1000))
    email: Mapped[str | None] = mapped_column(String(320))
    relevance_reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(80))

    job: Mapped["Job"] = relationship(back_populates="contacts")
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class OutreachMessage(TimestampMixin, Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contact: Mapped[Contact] = relationship(back_populates="outreach_messages")
    application: Mapped["Application | None"] = relationship(back_populates="outreach_messages")
