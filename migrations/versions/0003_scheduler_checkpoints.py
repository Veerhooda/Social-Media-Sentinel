"""Add scheduler checkpoints and graph processing state.

Revision ID: 0003_scheduler
Revises: 0002_bertrend
Create Date: 2026-09-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_scheduler"
down_revision: str | None = "0002_bertrend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "social_events",
        sa.Column("graph_processed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_events_graph_pending",
        "social_events",
        ["graph_processed_at"],
    )
    op.create_table(
        "analytics_checkpoints",
        sa.Column("job_name", sa.String(64), primary_key=True),
        sa.Column("cursor_value", sa.String(256)),
        sa.Column("last_event_collected_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("analytics_checkpoints")
    op.drop_index("ix_events_graph_pending", table_name="social_events")
    op.drop_column("social_events", "graph_processed_at")
