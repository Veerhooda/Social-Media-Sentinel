"""Drop the abandoned draft-review prototype tables (superseded by the Audience Lab).

Revision ID: 0007_drop_draft_reviews
Revises: 0006_audience_lab

Databases that once applied the unreleased ``0005_audience_reviews`` revision
still contain these tables; fresh databases never had them, hence IF EXISTS.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007_drop_draft_reviews"
down_revision: str | None = "0006_audience_lab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS draft_reviews")
    op.execute("DROP TABLE IF EXISTS audience_cohort_snapshots")


def downgrade() -> None:
    """Nothing to restore: the prototype tables are intentionally gone."""
