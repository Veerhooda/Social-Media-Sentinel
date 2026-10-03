from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class CollectionSource(Base):
    """One collection target. Collectors read enabled rows on every run."""

    __tablename__ = "collection_sources"
    __table_args__ = (UniqueConstraint("platform", "target", name="uq_collection_source_target"),)

    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[str | None] = mapped_column(String(256))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cursor: Mapped[str | None] = mapped_column(String(256))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_detail: Mapped[str | None] = mapped_column(Text)
    last_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
