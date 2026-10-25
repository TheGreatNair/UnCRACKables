"""Create normalized field reports table.

Revision ID: 0001_reports
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_reports"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("review_status", sa.String(length=32), server_default="not_reviewed", nullable=False),
        sa.Column("reporter_subject", sa.String(length=200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_received_at", "reports", ["received_at"], unique=False)


def downgrade() -> None:
    raise RuntimeError(
        "Dropping reports is destructive. Back up and handle schema removal manually."
    )
