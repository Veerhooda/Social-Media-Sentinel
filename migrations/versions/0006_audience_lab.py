"""Audience Lab: extensible audience profiles, model-built segments, post simulations.

Revision ID: 0006_audience_lab
Revises: 0004_demographics
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0006_audience_lab"
down_revision: str | None = "0004_demographics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audience_profiles",
        sa.Column("profile_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("external_ref", sa.String(256), nullable=False),
        sa.Column("platform", sa.String(32)),
        sa.Column("label", sa.String(256)),
        sa.Column("attributes", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("behaviour", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sample_texts", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("social_user_id", UUID(as_uuid=True), sa.ForeignKey("social_users.user_id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "external_ref", name="uq_audience_profile_source_ref"),
    )
    op.create_index("ix_audience_profiles_source", "audience_profiles", ["source"])
    op.create_table(
        "audience_segmentations",
        sa.Column("segmentation_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("params", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("profile_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text()),
        sa.Column("progress", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_audience_segmentations_created", "audience_segmentations", [sa.desc("created_at")])
    op.create_table(
        "audience_segments",
        sa.Column("segment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("segmentation_id", UUID(as_uuid=True), sa.ForeignKey("audience_segmentations.segmentation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("defining_traits", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("share", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attribute_breakdown", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("persona", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audience_segments_segmentation", "audience_segments", ["segmentation_id"])
    op.create_table(
        "audience_segment_members",
        sa.Column("segment_id", UUID(as_uuid=True), sa.ForeignKey("audience_segments.segment_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("audience_profiles.profile_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confidence", sa.Float()),
    )
    op.create_table(
        "post_simulations",
        sa.Column("simulation_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("segmentation_id", UUID(as_uuid=True), sa.ForeignKey("audience_segmentations.segmentation_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("post_text", sa.Text(), nullable=False),
        sa.Column("media", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("progress", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("baseline", JSONB()),
        sa.Column("analysis", JSONB()),
        sa.Column("improved_post", sa.Text()),
        sa.Column("improved", JSONB()),
        sa.Column("uplift", JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_post_simulations_created", "post_simulations", [sa.desc("created_at")])


def downgrade() -> None:
    op.drop_index("ix_post_simulations_created", table_name="post_simulations")
    op.drop_table("post_simulations")
    op.drop_table("audience_segment_members")
    op.drop_index("ix_audience_segments_segmentation", table_name="audience_segments")
    op.drop_table("audience_segments")
    op.drop_index("ix_audience_segmentations_created", table_name="audience_segmentations")
    op.drop_table("audience_segmentations")
    op.drop_index("ix_audience_profiles_source", table_name="audience_profiles")
    op.drop_table("audience_profiles")
