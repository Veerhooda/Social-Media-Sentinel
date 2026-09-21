from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SocialUser(Base):
    __tablename__ = "social_users"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_user_platform_id"),)

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(256))
    bio: Mapped[str | None] = mapped_column(Text)
    location_raw: Mapped[str | None] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    followers_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    following_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_verified: Mapped[bool | None] = mapped_column(Boolean)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SocialEvent(Base):
    __tablename__ = "social_events"
    __table_args__ = (
        UniqueConstraint("platform", "platform_post_id", name="uq_event_platform_post"),
        Index("ix_events_platform_created", "platform", desc("created_at")),
        Index("ix_events_author", "author_id"),
        Index("ix_events_created_at", desc("created_at")),
        Index("ix_events_collected_at", desc("collected_at")),
        Index("ix_events_parent_platform_post", "platform", "parent_platform_post_id"),
        Index("ix_events_hashtags_gin", "hashtags", postgresql_using="gin"),
        Index("ix_events_graph_pending", "graph_processed_at"),
    )

    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_platform_post_id: Mapped[str | None] = mapped_column(String(128))
    thread_root_id: Mapped[str | None] = mapped_column(String(128))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("social_users.user_id"), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language_code: Mapped[str | None] = mapped_column(String(16))
    hashtags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    mentions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    media: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    relationships: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    graph_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NLPAnalysis(Base):
    __tablename__ = "nlp_analysis"
    __table_args__ = (UniqueConstraint("event_id", name="uq_nlp_event"),)

    analysis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.event_id", ondelete="CASCADE"), nullable=False
    )
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_scores: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    is_ironic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    irony_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    irony_scores: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    primary_emotion: Mapped[str | None] = mapped_column(String(64))
    emotion_scores: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    stance_target: Mapped[str | None] = mapped_column(String(256))
    stance_label: Mapped[str | None] = mapped_column(String(32))
    stance_confidence: Mapped[float | None] = mapped_column(Float)
    stance_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_versions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserDemographic(Base):
    __tablename__ = "user_demographics"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_demographics_user"),
        Index("ix_demographics_language", "primary_language"),
        Index("ix_demographics_sector", "professional_sector"),
        Index("ix_demographics_country", "inferred_country"),
    )

    demographic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_users.user_id", ondelete="CASCADE"), nullable=False
    )
    age_bracket: Mapped[str | None] = mapped_column(String(16))
    age_confidence: Mapped[float | None] = mapped_column(Float)
    inferred_country: Mapped[str | None] = mapped_column(String(8))
    inferred_region: Mapped[str | None] = mapped_column(String(128))
    primary_language: Mapped[str | None] = mapped_column(String(16))
    professional_sector: Mapped[str | None] = mapped_column(String(128))
    profession_confidence: Mapped[float | None] = mapped_column(Float)
    gender: Mapped[str | None] = mapped_column(String(32))
    gender_confidence: Mapped[float | None] = mapped_column(Float)
    language_confidence: Mapped[float | None] = mapped_column(Float)
    geography_confidence: Mapped[float | None] = mapped_column(Float)
    inference_source: Mapped[str | None] = mapped_column(String(64))
    model_versions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "source_platform_user_id", "target_platform_user_id", "interaction_type",
            name="uq_graph_event_relation",
        ),
        Index("ix_graph_source", "platform", "source_platform_user_id"),
        Index("ix_graph_target", "platform", "target_platform_user_id"),
        Index("ix_graph_occurred", desc("occurred_at")),
    )

    edge_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.event_id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_platform_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_platform_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("topic_key", name="uq_topic_key"),)

    topic_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_key: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    model_name: Mapped[str | None] = mapped_column(String(256))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrendMeasurement(Base):
    __tablename__ = "trend_measurements"
    __table_args__ = (
        UniqueConstraint(
            "topic_id", "window_start", "window_end", name="uq_trend_topic_window"
        ),
        Index("ix_trend_time", "window_start", "window_end"),
    )

    measurement_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False)
    growth_score: Mapped[float | None] = mapped_column(Float)
    velocity_score: Mapped[float | None] = mapped_column(Float)
    acceleration_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(32))
    sentiment_distribution: Mapped[dict[str, float]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    analysis_engine: Mapped[str | None] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"

    dead_letter_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[str | None] = mapped_column(String(32))
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsCheckpoint(Base):
    __tablename__ = "analytics_checkpoints"

    job_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    cursor_value: Mapped[str | None] = mapped_column(String(256))
    last_event_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
