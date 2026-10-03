"""ORM tables for the Audience Lab.

``audience_profiles`` is the open-ended audience mapping store: any source
(scraped social users, CRM exports, survey panels, manual personas) can add
rows with arbitrary ``attributes``. Segmentations, segments and post
simulations are immutable runs that reference those profiles.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class AudienceProfile(Base):
    __tablename__ = "audience_profiles"
    __table_args__ = (
        UniqueConstraint("source", "external_ref", name="uq_audience_profile_source_ref"),
        Index("ix_audience_profiles_source", "source"),
    )

    profile_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32))
    label: Mapped[str | None] = mapped_column(String(256))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    behaviour: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sample_texts: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    social_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("social_users.user_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AudienceSegmentation(Base):
    __tablename__ = "audience_segmentations"
    __table_args__ = (Index("ix_audience_segmentations_created", desc("created_at")),)

    segmentation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    profile_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rationale: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AudienceSegment(Base):
    __tablename__ = "audience_segments"
    __table_args__ = (Index("ix_audience_segments_segmentation", "segmentation_id"),)

    segment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    segmentation_id: Mapped[UUID] = mapped_column(
        ForeignKey("audience_segmentations.segmentation_id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    defining_traits: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weight_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attribute_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    persona: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AudienceSegmentMember(Base):
    __tablename__ = "audience_segment_members"

    segment_id: Mapped[UUID] = mapped_column(
        ForeignKey("audience_segments.segment_id", ondelete="CASCADE"), primary_key=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("audience_profiles.profile_id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float | None] = mapped_column(Float)


class PostSimulation(Base):
    __tablename__ = "post_simulations"
    __table_args__ = (Index("ix_post_simulations_created", desc("created_at")),)

    simulation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    segmentation_id: Mapped[UUID] = mapped_column(
        ForeignKey("audience_segmentations.segmentation_id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    media: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    baseline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    improved_post: Mapped[str | None] = mapped_column(Text)
    improved: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    uplift: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
