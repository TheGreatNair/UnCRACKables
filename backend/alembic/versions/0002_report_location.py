"""Add optional report location metadata.

Revision ID: 0002_report_location
Revises: 0001_reports
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_report_location"
down_revision: Union[str, None] = "0001_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("reports", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("reports", sa.Column("location_source", sa.String(length=16), nullable=True))
    op.add_column("reports", sa.Column("location_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Dropping report location columns would delete captured coordinates.")
