"""Add scoped authorization, review notes, and audit events.

Revision ID: 0003_authz_audit
Revises: 0002_report_location
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_authz_audit"
down_revision: Union[str, None] = "0002_report_location"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("review_notes", sa.Text(), nullable=True))

    op.create_table(
        "user_roles",
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("granted_by", sa.String(length=200), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('reviewer', 'administrator')", name="ck_user_roles_role"),
        sa.PrimaryKeyConstraint("subject", "role"),
    )
    op.create_index("ix_user_roles_role", "user_roles", ["role"], unique=False)

    op.create_table(
        "reviewer_scopes",
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("granted_by", sa.String(length=200), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("subject", "sector"),
    )
    op.create_index("ix_reviewer_scopes_sector", "reviewer_scopes", ["sector"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_subject", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)
    op.create_index(
        "ix_audit_events_actor_created_at",
        "audit_events",
        ["actor_subject", "created_at"],
        unique=False,
    )

    # The Expo app and dashboard use Supabase Auth only; all report data must
    # pass through the role-checked FastAPI service. Supabase projects can grant
    # public-schema tables to these API roles by default, so revoke table access
    # explicitly. The backend uses a separate PostgreSQL login role.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "REVOKE ALL PRIVILEGES ON TABLE "
            "public.reports, public.user_roles, public.reviewer_scopes, public.audit_events "
            "FROM anon, authenticated"
        )


def downgrade() -> None:
    connection = op.get_bind()
    nonempty_tables = (
        "user_roles",
        "reviewer_scopes",
        "audit_events",
    )
    for table in nonempty_tables:
        count = connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
        if count:
            raise RuntimeError(f"Refusing downgrade because {table} contains security data")
    review_notes = connection.execute(
        sa.text("SELECT count(*) FROM reports WHERE review_notes IS NOT NULL")
    ).scalar_one()
    if review_notes:
        raise RuntimeError("Refusing downgrade because reports contain review notes")

    op.drop_index("ix_audit_events_actor_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_reviewer_scopes_sector", table_name="reviewer_scopes")
    op.drop_table("reviewer_scopes")
    op.drop_index("ix_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_column("reports", "review_notes")
