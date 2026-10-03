"""Configurable collection sources (Telegram channels, YouTube videos, X queries).

Revision ID: 0008_collection_sources
Revises: 0007_drop_draft_reviews
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008_collection_sources"
down_revision: str | None = "0007_drop_draft_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collection_sources",
        sa.Column("source_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("target", sa.String(512), nullable=False),
        sa.Column("label", sa.String(256)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cursor", sa.String(256)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_status", sa.String(16)),
        sa.Column("last_detail", sa.Text()),
        sa.Column("last_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("platform", "target", name="uq_collection_source_target"),
    )


def downgrade() -> None:
    op.drop_table("collection_sources")
