from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from haxjobs_api.database import Base
from haxjobs_api.features.shared import TimestampMixin, new_id


class ApplicationPack(TimestampMixin, Base):
    __tablename__ = "application_packs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(250), nullable=False)
    based_on_pack_id: Mapped[str | None] = mapped_column(ForeignKey("application_packs.id", ondelete="SET NULL"))
    generation_mode: Mapped[str | None] = mapped_column(String(100))
    fit_summary: Mapped[str | None] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="packs")
    documents: Mapped[list["Document"]] = relationship(back_populates="pack", cascade="all, delete-orphan")
