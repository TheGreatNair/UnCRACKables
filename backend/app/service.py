from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditEvent, ReportRecord
from app.schemas import ReportCreate


class ReportIdConflict(Exception):
    """The same report ID was reused for different observation data."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _matches(record: ReportRecord, report: ReportCreate, reporter_subject: str) -> bool:
    return (
        record.reporter_subject == reporter_subject
        and
        record.sector == report.sector
        and record.report_type == report.report_type
        and record.notes == report.notes
        and _as_utc(record.observed_at) == _as_utc(report.timestamp)
        and record.latitude == report.latitude
        and record.longitude == report.longitude
        and record.location_source == report.location_source
        and record.location_name == report.location_name
    )


def create_or_get_report(
    session: Session, report: ReportCreate, reporter_subject: str
) -> tuple[ReportRecord, bool]:
    existing = session.get(ReportRecord, report.id)
    if existing is not None:
        if not _matches(existing, report, reporter_subject):
            raise ReportIdConflict(report.id)
        return existing, False

    record = ReportRecord(
        id=report.id,
        sector=report.sector,
        report_type=report.report_type,
        notes=report.notes,
        observed_at=report.timestamp,
        latitude=report.latitude,
        longitude=report.longitude,
        location_source=report.location_source,
        location_name=report.location_name,
        received_at=datetime.now(timezone.utc),
        review_status="not_reviewed",
        reporter_subject=reporter_subject,
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request may have inserted this ID after our initial read.
        session.rollback()
        concurrent = session.get(ReportRecord, report.id)
        if concurrent is None or not _matches(concurrent, report, reporter_subject):
            raise ReportIdConflict(report.id)
        return concurrent, False
    session.refresh(record)
    return record, True


def response_payload(record: ReportRecord, *, include_review_notes: bool = False) -> dict:
    payload = {
        "id": record.id,
        "sector": record.sector,
        "type": record.report_type,
        "notes": record.notes,
        "timestamp": _as_utc(record.observed_at),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "locationSource": record.location_source,
        "locationName": record.location_name,
        "createdAt": _as_utc(record.observed_at),
        "receivedAt": _as_utc(record.received_at),
        "syncStatus": "synced",
        "reviewStatus": record.review_status,
    }
    if include_review_notes:
        payload["reviewNotes"] = record.review_notes
    return payload


def append_audit_event(
    session: Session,
    *,
    actor_subject: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=str(uuid4()),
        actor_subject=actor_subject,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        event_metadata=metadata or {},
    )
    session.add(event)
    return event
