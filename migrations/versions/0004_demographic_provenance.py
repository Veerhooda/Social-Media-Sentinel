"""Add demographic provenance columns.

Revision ID: 0004_demographics
Revises: 0003_scheduler
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004_demographics"
down_revision: str | None = "0003_scheduler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_demographics",
        sa.Column("language_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "user_demographics",
        sa.Column("geography_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "user_demographics",
        sa.Column("inference_source", sa.String(64), nullable=True),
    )
    op.add_column(
        "user_demographics",
        sa.Column("model_versions", JSONB, nullable=False, server_default="{}"),
    )
    op.add_column(
        "user_demographics",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_demographics_language",
        "user_demographics",
        ["primary_language"],
    )
    op.create_index(
        "ix_demographics_sector",
        "user_demographics",
        ["professional_sector"],
    )
    op.create_index(
        "ix_demographics_country",
        "user_demographics",
        ["inferred_country"],
    )


def downgrade() -> None:
    op.drop_index("ix_demographics_country", table_name="user_demographics")
    op.drop_index("ix_demographics_sector", table_name="user_demographics")
    op.drop_index("ix_demographics_language", table_name="user_demographics")
    op.drop_column("user_demographics", "updated_at")
    op.drop_column("user_demographics", "model_versions")
    op.drop_column("user_demographics", "inference_source")
    op.drop_column("user_demographics", "geography_confidence")
    op.drop_column("user_demographics", "language_confidence")
