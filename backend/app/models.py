from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReportRecord(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_received_at", "received_at"),)

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    report_type: Mapped[str] = mapped_column("type", String(120), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Review state is server-owned. These fields leave room for a later
    # authenticated reviewer workflow without trusting the mobile client.
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_reviewed", server_default="not_reviewed"
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporter_subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        CheckConstraint("role IN ('reviewer', 'administrator')", name="ck_user_roles_role"),
        Index("ix_user_roles_role", "role"),
    )

    subject: Mapped[str] = mapped_column(String(200), primary_key=True)
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    granted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewerScope(Base):
    __tablename__ = "reviewer_scopes"
    __table_args__ = (Index("ix_reviewer_scopes_sector", "sector"),)

    subject: Mapped[str] = mapped_column(String(200), primary_key=True)
    sector: Mapped[str] = mapped_column(String(120), primary_key=True)
    granted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_actor_created_at", "actor_subject", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_subject: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
