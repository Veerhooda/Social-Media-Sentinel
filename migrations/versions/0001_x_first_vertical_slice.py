"""Create the X-first canonical analytics schema.

Revision ID: 0001_x_first
Revises:
Create Date: 2026-09-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_x_first"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table(
        "social_users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("platform_user_id", sa.String(128), nullable=False),
        sa.Column("username", sa.String(128)),
        sa.Column("display_name", sa.String(256)),
        sa.Column("bio", sa.Text()),
        sa.Column("location_raw", sa.String(256)),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("followers_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("following_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_verified", sa.Boolean()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("platform", "platform_user_id", name="uq_user_platform_id"),
    )
    op.create_table(
        "social_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("platform_post_id", sa.String(128), nullable=False),
        sa.Column("parent_platform_post_id", sa.String(128)),
        sa.Column("thread_root_id", sa.String(128)),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("social_users.user_id"), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("language_code", sa.String(16)),
        sa.Column("hashtags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("mentions", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("media", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("relationships", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("platform", "platform_post_id", name="uq_event_platform_post"),
    )
    op.create_index("ix_events_platform_created", "social_events", ["platform", sa.text("created_at DESC")])
    op.create_index("ix_events_author", "social_events", ["author_id"])
    op.create_index("ix_events_created_at", "social_events", [sa.text("created_at DESC")])
    op.create_index("ix_events_collected_at", "social_events", [sa.text("collected_at DESC")])
    op.create_index("ix_events_parent_platform_post", "social_events", ["platform", "parent_platform_post_id"])
    op.create_index("ix_events_hashtags_gin", "social_events", ["hashtags"], postgresql_using="gin")

    op.create_table(
        "nlp_analysis",
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("social_events.event_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sentiment_label", sa.String(16), nullable=False),
        sa.Column("sentiment_confidence", sa.Float(), nullable=False),
        sa.Column("sentiment_scores", postgresql.JSONB(), nullable=False),
        sa.Column("is_ironic", sa.Boolean(), nullable=False),
        sa.Column("irony_confidence", sa.Float(), nullable=False),
        sa.Column("irony_scores", postgresql.JSONB(), nullable=False),
        sa.Column("primary_emotion", sa.String(64)),
        sa.Column("emotion_scores", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("stance_target", sa.String(256)),
        sa.Column("stance_label", sa.String(32)),
        sa.Column("stance_confidence", sa.Float()),
        sa.Column("stance_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model_versions", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", name="uq_nlp_event"),
    )
    op.create_table(
        "user_demographics",
        sa.Column("demographic_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("social_users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("age_bracket", sa.String(16)),
        sa.Column("age_confidence", sa.Float()),
        sa.Column("inferred_country", sa.String(8)),
        sa.Column("inferred_region", sa.String(128)),
        sa.Column("primary_language", sa.String(16)),
        sa.Column("professional_sector", sa.String(128)),
        sa.Column("profession_confidence", sa.Float()),
        sa.Column("gender", sa.String(32)),
        sa.Column("gender_confidence", sa.Float()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_demographics_user"),
    )
    op.create_table(
        "topics",
        sa.Column("topic_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "trend_measurements",
        sa.Column("measurement_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic_id", sa.BigInteger(), sa.ForeignKey("topics.topic_id"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("velocity_score", sa.Float()),
        sa.Column("acceleration_score", sa.Float()),
        sa.Column("status", sa.String(32)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_trend_time", "trend_measurements", ["window_start", "window_end"])
    op.create_table(
        "graph_edges",
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("social_events.event_id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("source_platform_user_id", sa.String(128), nullable=False),
        sa.Column("target_platform_user_id", sa.String(128), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "event_id", "source_platform_user_id", "target_platform_user_id", "interaction_type",
            name="uq_graph_event_relation",
        ),
    )
    op.create_index("ix_graph_source", "graph_edges", ["platform", "source_platform_user_id"])
    op.create_index("ix_graph_target", "graph_edges", ["platform", "target_platform_user_id"])
    op.create_index("ix_graph_occurred", "graph_edges", [sa.text("occurred_at DESC")])
    op.create_table(
        "dead_letter_events",
        sa.Column("dead_letter_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform", sa.String(32)),
        sa.Column("error_type", sa.String(128), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB()),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("dead_letter_events")
    op.drop_table("graph_edges")
    op.drop_table("trend_measurements")
    op.drop_table("topics")
    op.drop_table("user_demographics")
    op.drop_table("nlp_analysis")
    op.drop_table("social_events")
    op.drop_table("social_users")

