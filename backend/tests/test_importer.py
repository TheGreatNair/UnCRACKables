import json
import sqlite3
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, build_engine
from app.importer import ImportConflictError, import_sqlite_reports
from app.models import ReportRecord


def make_source(path, reports: list[dict]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE reports (id TEXT PRIMARY KEY, payload TEXT NOT NULL, received_at TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO reports (id, payload, received_at) VALUES (?, ?, ?)",
            [
                (report["id"], json.dumps(report), "2026-10-24T12:30:00+00:00")
                for report in reports
            ],
        )


def sample_report(report_id: str = "legacy-001") -> dict:
    return {
        "id": report_id,
        "sector": "Panambur",
        "type": "Turtle sighting",
        "notes": "Imported report",
        "timestamp": "2026-10-24T12:00:00+00:00",
        "syncStatus": "synced",
        # Legacy client data must not become an authority review.
        "reviewStatus": "reviewed",
    }


def test_import_verifies_ids_and_repeated_runs_are_safe(tmp_path) -> None:
    source = tmp_path / "legacy.db"
    make_source(source, [sample_report(), sample_report("legacy-002")])
    target = build_engine(f"sqlite:///{(tmp_path / 'target.db').as_posix()}")
    Base.metadata.create_all(target)

    first = import_sqlite_reports(source, target)
    second = import_sqlite_reports(source, target)
    assert (first.source_count, first.inserted_count, first.already_present_count, first.verified_count) == (2, 2, 0, 2)
    assert (second.source_count, second.inserted_count, second.already_present_count, second.verified_count) == (2, 0, 2, 2)
    with target.connect() as connection:
        assert connection.execute(select(ReportRecord.id).order_by(ReportRecord.id)).scalars().all() == ["legacy-001", "legacy-002"]
        assert connection.execute(select(ReportRecord.review_status).order_by(ReportRecord.id)).scalars().all() == ["not_reviewed", "not_reviewed"]
    target.dispose()


def test_import_conflict_rolls_back_all_rows(tmp_path) -> None:
    source = tmp_path / "legacy.db"
    make_source(source, [sample_report("legacy-new"), sample_report("legacy-conflict")])
    target = build_engine(f"sqlite:///{(tmp_path / 'target.db').as_posix()}")
    Base.metadata.create_all(target)
    with Session(target) as session:
        session.add(ReportRecord(
            id="legacy-conflict",
            sector="Tannirbhavi",
            report_type="Nest found",
            notes="Different target data",
            observed_at=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
            received_at=datetime(2026, 10, 24, 12, 30, tzinfo=timezone.utc),
            review_status="not_reviewed",
        ))
        session.commit()

    with pytest.raises(ImportConflictError):
        import_sqlite_reports(source, target)
    with target.connect() as connection:
        assert connection.execute(select(ReportRecord.id).order_by(ReportRecord.id)).scalars().all() == ["legacy-conflict"]
    target.dispose()


def test_importer_preserves_new_location_fields_and_accepts_legacy_payload(tmp_path) -> None:
    source = tmp_path / "legacy-with-location.db"
    gps_report = {
        **sample_report("gps-report"),
        "latitude": 12.8768,
        "longitude": 74.8421,
        "locationSource": "gps",
        "locationName": "Current Location",
    }
    old_report = sample_report("old-report")
    target = build_engine(f"sqlite:///{(tmp_path / 'target.db').as_posix()}")
    Base.metadata.create_all(target)
    make_source(source, [gps_report, old_report])

    summary = import_sqlite_reports(source, target)
    assert summary.verified_count == 2
    with target.connect() as connection:
        gps = connection.execute(
            select(
                ReportRecord.latitude,
                ReportRecord.longitude,
                ReportRecord.location_source,
                ReportRecord.location_name,
            ).where(ReportRecord.id == "gps-report")
        ).one()
        old = connection.execute(
            select(ReportRecord.latitude, ReportRecord.longitude).where(ReportRecord.id == "old-report")
        ).one()
        assert tuple(gps) == (
            12.8768, 74.8421, "gps", "Current Location"
        )
        assert tuple(old) == (None, None)
    target.dispose()
