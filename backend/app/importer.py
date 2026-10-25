import json
import logging
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.models import ReportRecord


logger = logging.getLogger("turtleway.importer")


class ImportValidationError(RuntimeError):
    pass


class ImportConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportSummary:
    source_count: int
    inserted_count: int
    already_present_count: int
    verified_count: int


def _parse_datetime(value: str | datetime, *, field: str) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ImportValidationError(f"Invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _source_rows(source_path: Path) -> list[tuple[str, dict, datetime]]:
    if not source_path.is_file():
        raise ImportValidationError(f"SQLite source file does not exist: {source_path}")
    uri = source_path.resolve().as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as source:
            table = source.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'reports'"
            ).fetchone()
            if table is None:
                raise ImportValidationError("SQLite source has no reports table")
            rows = source.execute(
                "SELECT id, payload, received_at FROM reports ORDER BY id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise ImportValidationError(f"Could not read SQLite source: {exc}") from exc

    if len(rows) != len({row[0] for row in rows}):
        raise ImportValidationError("SQLite source contains duplicate report IDs")

    validated: list[tuple[str, dict, datetime]] = []
    for report_id, raw_payload, received_at in rows:
        if not isinstance(report_id, str) or not report_id.strip() or len(report_id) > 100:
            raise ImportValidationError(f"SQLite row has an invalid report ID: {report_id!r}")
        try:
            payload = json.loads(raw_payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ImportValidationError(f"Report {report_id!r} has invalid JSON payload") from exc
        if not isinstance(payload, dict) or payload.get("id") != report_id:
            raise ImportValidationError(f"Report ID mismatch in SQLite row {report_id!r}")
        sector = payload.get("sector")
        report_type = payload.get("type")
        if not isinstance(sector, str) or not sector.strip():
            raise ImportValidationError(f"Report {report_id!r} has no valid sector")
        if not isinstance(report_type, str) or not report_type.strip():
            raise ImportValidationError(f"Report {report_id!r} has no valid type")
        if len(sector) > 120 or len(report_type) > 120:
            raise ImportValidationError(f"Report {report_id!r} exceeds a database field limit")
        notes = payload.get("notes") or ""
        if not isinstance(notes, str) or len(notes) > 20_000:
            raise ImportValidationError(f"Report {report_id!r} has invalid notes")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        location_source = payload.get("locationSource")
        location_name = payload.get("locationName")
        if (latitude is None) != (longitude is None):
            raise ImportValidationError(f"Report {report_id!r} must contain both coordinates or neither")
        if latitude is not None:
            if isinstance(latitude, bool) or not isinstance(latitude, (int, float)) or not math.isfinite(latitude) or not -90 <= latitude <= 90:
                raise ImportValidationError(f"Report {report_id!r} has invalid latitude")
            if isinstance(longitude, bool) or not isinstance(longitude, (int, float)) or not math.isfinite(longitude) or not -180 <= longitude <= 180:
                raise ImportValidationError(f"Report {report_id!r} has invalid longitude")
        if location_source not in (None, "gps", "preset", "manual"):
            raise ImportValidationError(f"Report {report_id!r} has invalid locationSource")
        if location_source == "gps" and latitude is None:
            raise ImportValidationError(f"GPS report {report_id!r} has no coordinates")
        if location_name is not None and (not isinstance(location_name, str) or len(location_name) > 200):
            raise ImportValidationError(f"Report {report_id!r} has invalid locationName")
        observed_value = payload.get("timestamp") or payload.get("createdAt") or received_at
        validated.append((report_id, payload, _parse_datetime(received_at, field="received_at")))
        # Validate observed time now so an invalid source cannot partially import.
        _parse_datetime(observed_value, field=f"timestamp for {report_id}")
    return validated


def _payload_matches(record: ReportRecord, payload: dict, received_at: datetime) -> bool:
    observed_value = payload.get("timestamp") or payload.get("createdAt") or received_at.isoformat()
    if not observed_value:
        return False
    try:
        observed_at = _parse_datetime(observed_value, field="timestamp")
    except ImportValidationError:
        return False
    record_observed = record.observed_at
    if record_observed.tzinfo is None:
        record_observed = record_observed.replace(tzinfo=timezone.utc)
    return (
        record.sector == (payload.get("sector") or "").strip()
        and record.report_type == (payload.get("type") or "").strip()
        and record.notes == (payload.get("notes") or "")
        and record_observed.astimezone(timezone.utc) == observed_at
        and record.latitude == payload.get("latitude")
        and record.longitude == payload.get("longitude")
        and record.location_source == payload.get("locationSource")
        and record.location_name == payload.get("locationName")
    )


def import_sqlite_reports(source_path: Path, target_engine: Engine) -> ImportSummary:
    """Import without writing to the source; safe to repeat for identical report IDs."""
    rows = _source_rows(source_path)
    ids = {report_id for report_id, _, _ in rows}
    SessionFactory = sessionmaker(bind=target_engine, expire_on_commit=False)
    inserted = 0
    present = 0
    with SessionFactory() as session:
        try:
            for report_id, payload, received_at in rows:
                existing = session.get(ReportRecord, report_id)
                if existing is not None:
                    if not _payload_matches(existing, payload, received_at):
                        raise ImportConflictError(
                            f"Target report {report_id!r} already exists with different data; no import committed"
                        )
                    present += 1
                    continue

                observed_value = payload.get("timestamp") or payload.get("createdAt") or received_at.isoformat()
                observed_at = _parse_datetime(observed_value, field=f"timestamp for {report_id}")
                session.add(ReportRecord(
                    id=report_id,
                    sector=payload["sector"].strip(),
                    report_type=payload["type"].strip(),
                    notes=payload.get("notes") or "",
                    observed_at=observed_at,
                    received_at=received_at,
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                    location_source=payload.get("locationSource"),
                    location_name=payload.get("locationName"),
                    # Legacy payload values were client supplied and are not trusted as reviews.
                    review_status="not_reviewed",
                    reviewed_at=None,
                    reviewed_by=None,
                ))
                inserted += 1
            session.flush()
            verified_ids = set(session.scalars(
                select(ReportRecord.id).where(ReportRecord.id.in_(ids))
            ).all()) if ids else set()
            if verified_ids != ids:
                raise ImportValidationError(
                    f"Post-import ID verification failed: source={len(ids)}, target={len(verified_ids)}"
                )
            if inserted + present != len(rows):
                raise ImportValidationError(
                    f"Count verification failed: source={len(rows)}, processed={inserted + present}"
                )
            session.commit()
        except Exception:
            session.rollback()
            raise

    logger.info(
        "SQLite import verified: source=%d inserted=%d already_present=%d target_ids_verified=%d",
        len(rows), inserted, present, len(ids),
    )
    return ImportSummary(len(rows), inserted, present, len(verified_ids))
