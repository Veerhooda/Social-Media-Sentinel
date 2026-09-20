"""Extend topics and measurements for BERTrend persistence.

Revision ID: 0002_bertrend
Revises: 0001_x_first
Create Date: 2026-09-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_bertrend"
down_revision: str | None = "0001_x_first"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("topic_key", sa.String(128)))
    op.add_column("topics", sa.Column("model_name", sa.String(256)))
    op.create_unique_constraint("uq_topic_key", "topics", ["topic_key"])

    op.add_column("trend_measurements", sa.Column("growth_score", sa.Float()))
    op.add_column(
        "trend_measurements",
        sa.Column(
            "sentiment_distribution",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("trend_measurements", sa.Column("analysis_engine", sa.String(128)))
    op.create_unique_constraint(
        "uq_trend_topic_window",
        "trend_measurements",
        ["topic_id", "window_start", "window_end"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_trend_topic_window", "trend_measurements", type_="unique")
    op.drop_column("trend_measurements", "analysis_engine")
    op.drop_column("trend_measurements", "sentiment_distribution")
    op.drop_column("trend_measurements", "growth_score")

    op.drop_constraint("uq_topic_key", "topics", type_="unique")
    op.drop_column("topics", "model_name")
    op.drop_column("topics", "topic_key")
