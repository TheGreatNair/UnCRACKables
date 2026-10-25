from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.auth import AuthenticatedUser, InvalidAccessToken, verify_access_token
from app.config import Settings, ensure_api_access_policy
from app.main import app
from app.models import AuditEvent, ReportRecord, ReviewerScope, UserRole
from app.schemas import ReportCreate
from app.service import ReportIdConflict, create_or_get_report
TEST_REPORTER_ID = "11111111-1111-4111-8111-111111111111"


def _seed_report(session: Session, report_id: str, sector: str, owner: str | None = TEST_REPORTER_ID) -> None:
    session.add(ReportRecord(
        id=report_id,
        sector=sector,
        report_type="Turtle sighting",
        notes="Seeded test report",
        observed_at=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
        received_at=datetime(2026, 10, 24, 12, 1, tzinfo=timezone.utc),
        reporter_subject=owner,
        review_status="not_reviewed",
    ))
    session.commit()


def test_health_is_public_and_checks_database(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ok"


def test_reports_require_a_valid_bearer_session(client: TestClient) -> None:
    from app.auth import get_current_user

    app.dependency_overrides.pop(get_current_user)
    assert client.get("/reports").status_code == 401


def test_post_get_consistency_and_server_owned_fields(client: TestClient, report_payload: dict) -> None:
    posted = client.post("/reports", json=report_payload)
    assert posted.status_code == 200
    report = posted.json()["report"]
    assert posted.json()["success"] is True
    assert report["id"] == report_payload["id"]
    assert report["syncStatus"] == "synced"
    assert report["reviewStatus"] == "not_reviewed"
    assert report["receivedAt"]

    listed = client.get("/reports?limit=10&offset=0")
    assert listed.status_code == 200
    assert listed.json() == [report]


def test_repeated_identical_post_is_idempotent(client: TestClient, report_payload: dict) -> None:
    first = client.post("/reports", json=report_payload)
    second = client.post("/reports", json=report_payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["report"] == second.json()["report"]
    assert second.json()["duplicate"] is True
    assert len(client.get("/reports").json()) == 1


def test_same_id_with_different_payload_returns_conflict(client: TestClient, report_payload: dict) -> None:
    assert client.post("/reports", json=report_payload).status_code == 200
    conflict = client.post("/reports", json={**report_payload, "notes": "different observation"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "report_id_conflict"


def test_cross_user_id_reuse_and_report_reads_are_denied(client, report_payload: dict) -> None:
    from app.auth import get_current_user

    first = client.post("/reports", json=report_payload)
    assert first.status_code == 200
    second_user = str(uuid4())
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(second_user)
    assert client.get("/reports").json() == []
    assert client.get(f"/reports/{report_payload['id']}").status_code == 404
    assert client.post("/reports", json=report_payload).status_code == 409


def test_validation_rejects_invalid_timestamp_and_unknown_fields(client, report_payload: dict) -> None:
    invalid_timestamp = client.post("/reports", json={**report_payload, "timestamp": "yesterday"})
    unknown_field = client.post("/reports", json={**report_payload, "unexpected": "value"})
    assert invalid_timestamp.status_code == 422
    assert unknown_field.status_code == 422


def test_client_cannot_forge_review_fields(client, report_payload: dict) -> None:
    forged_status = client.post("/reports", json={**report_payload, "reviewStatus": "verified"})
    forged_reviewer = client.post("/reports", json={**report_payload, "reviewedBy": str(uuid4())})
    forged_note = client.post("/reports", json={**report_payload, "reviewNotes": "approved"})
    assert forged_status.status_code == 422
    assert forged_reviewer.status_code == 422
    assert forged_note.status_code == 422


def test_client_cannot_set_server_receipt_timestamp(client, report_payload: dict) -> None:
    response = client.post("/reports", json={**report_payload, "receivedAt": "2000-01-01T00:00:00Z"})
    assert response.status_code == 422


def test_legacy_pending_claim_is_ignored_and_pagination_is_bounded(client, report_payload: dict) -> None:
    posted = client.post("/reports", json={**report_payload, "syncStatus": "synced"})
    assert posted.status_code == 200
    assert posted.json()["report"]["syncStatus"] == "synced"
    assert client.get("/reports?limit=0").status_code == 422


def test_gps_coordinates_and_metadata_persist_and_return(client, report_payload: dict) -> None:
    gps_payload = {
        **report_payload,
        "sector": "Current Location",
        "latitude": 12.8768,
        "longitude": 74.8421,
        "locationSource": "gps",
        "locationName": "Current Location",
    }
    posted = client.post("/reports", json=gps_payload)
    assert posted.status_code == 200
    report = posted.json()["report"]
    assert (report["latitude"], report["longitude"]) == (12.8768, 74.8421)
    assert report["locationSource"] == "gps"
    assert report["locationName"] == "Current Location"
    assert client.get("/reports").json()[0] == report


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(90.0001, 0), (-90.0001, 0), (0, 180.0001), (0, -180.0001)],
)
def test_invalid_coordinates_are_rejected(client, report_payload, latitude, longitude) -> None:
    response = client.post(
        "/reports",
        json={**report_payload, "latitude": latitude, "longitude": longitude},
    )
    assert response.status_code == 422


def test_coordinates_must_be_a_pair_and_gps_requires_coordinates(client, report_payload) -> None:
    latitude_only = client.post("/reports", json={**report_payload, "latitude": 12.9})
    gps_without_coordinates = client.post("/reports", json={**report_payload, "locationSource": "gps"})
    assert latitude_only.status_code == 422
    assert gps_without_coordinates.status_code == 422


def test_reviewer_can_only_view_assigned_sector_and_review(client, test_session_factory):
    from app.auth import get_current_user

    reviewer_id = str(uuid4())
    with test_session_factory() as session:
        session.add(UserRole(subject=reviewer_id, role="reviewer", granted_by=str(uuid4())))
        session.add(ReviewerScope(subject=reviewer_id, sector="Panambur", granted_by=str(uuid4())))
        _seed_report(session, "review-panambur", "Panambur", owner=str(uuid4()))
        _seed_report(session, "review-tannirbhavi", "Tannirbhavi", owner=str(uuid4()))

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(reviewer_id)
    listed = client.get("/reports")
    assert [item["id"] for item in listed.json()] == ["review-panambur"]
    assert client.get("/reports/review-tannirbhavi").status_code == 404
    reviewed = client.patch("/reports/review-panambur/review", json={
        "reviewStatus": "in_review",
        "reviewNotes": "Check the nest evidence.",
    })
    assert reviewed.status_code == 200
    assert reviewed.json()["report"]["reviewStatus"] == "in_review"
    assert reviewed.json()["report"]["reviewNotes"] == "Check the nest evidence."
    with test_session_factory() as session:
        audit = session.scalars(select(AuditEvent).where(AuditEvent.action == "report.review_status_changed")).all()
        stored = session.get(ReportRecord, "review-panambur")
        assert len(audit) == 1
        assert stored.reviewed_by == reviewer_id


def test_invalid_review_transition_is_rejected(client, test_session_factory):
    from app.auth import get_current_user

    reviewer_id = str(uuid4())
    with test_session_factory() as session:
        session.add(UserRole(subject=reviewer_id, role="reviewer", granted_by=str(uuid4())))
        session.add(ReviewerScope(subject=reviewer_id, sector="Panambur", granted_by=str(uuid4())))
        _seed_report(session, "transition-report", "Panambur", owner=str(uuid4()))
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(reviewer_id)
    response = client.patch("/reports/transition-report/review", json={"reviewStatus": "verified"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_review_transition"


def test_admin_can_grant_and_revoke_reviewer_scope_with_audit(client, test_session_factory):
    admin_id = TEST_REPORTER_ID
    subject = str(uuid4())
    with test_session_factory() as session:
        session.add(UserRole(subject=admin_id, role="administrator", granted_by="bootstrap:operator"))
        session.commit()
    grant = client.put(f"/admin/reviewers/{subject}/sectors/Panambur")
    assert grant.status_code == 200 and grant.json()["created"] is True
    assert client.get("/reports").status_code == 200
    assert client.get("/admin/audit").status_code == 200
    revoke = client.delete(f"/admin/reviewers/{subject}/sectors/Panambur")
    assert revoke.status_code == 200
    with test_session_factory() as session:
        assert session.get(UserRole, (subject, "reviewer")) is None
        actions = session.scalars(select(AuditEvent.action)).all()
        assert "reviewer.scope_granted" in actions
        assert "reviewer.scope_revoked" in actions
        assert "reports.admin_list_read" in actions
        assert "audit_events.listed" in actions


def test_reporter_cannot_read_audit_and_denial_is_audited(client, test_session_factory):
    response = client.get("/admin/audit")
    assert response.status_code == 403
    with test_session_factory() as session:
        denied = session.scalars(select(AuditEvent).where(AuditEvent.action == "authorization.denied")).all()
        assert len(denied) == 1
        assert denied[0].actor_subject == TEST_REPORTER_ID


def test_request_body_limit_rejects_large_payload(client):
    response = client.post("/reports", content=b"x" * (1_048_576 + 1))
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "request_too_large"


def test_production_fails_closed_without_auth_configuration() -> None:
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="postgresql://turtleway_api.projectref:pass@host/db",
            cors_origins=["https://authority.example"],
        )
    production = Settings(
        app_env="production",
        database_url="postgresql://turtleway_api.projectref:pass@host/db",
        supabase_url="https://project.supabase.co",
        cors_origins=["https://authority.example"],
    )
    ensure_api_access_policy(production)
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="sqlite:///./not-allowed.db",
            supabase_url="https://project.supabase.co",
            cors_origins=["https://authority.example"],
        )
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="postgresql://postgres.projectref:pass@host/db",
            supabase_url="https://project.supabase.co",
            cors_origins=["https://authority.example"],
        )
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            database_url="postgresql://turtleway_api.projectref:pass@host/db",
            supabase_url="https://project.supabase.co",
            cors_origins=["*"],
        )


def test_supabase_jwt_signature_issuer_audience_and_expiry(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class FakeSigningKey:
        key = public_key

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(auth, "_jwks_client", lambda _: FakeJwksClient())
    config = Settings(app_env="test", supabase_url="https://project.supabase.co")
    valid_claims = {
        "sub": TEST_REPORTER_ID,
        "iss": config.supabase_issuer,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }

    valid = jwt.encode(valid_claims, private_key, algorithm="RS256", headers={"kid": "test-key"})
    assert verify_access_token(valid, config).subject == TEST_REPORTER_ID

    expired = jwt.encode({**valid_claims, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, private_key, algorithm="RS256", headers={"kid": "test-key"})
    malformed = "not.a.jwt"
    wrong_issuer = jwt.encode({**valid_claims, "iss": "https://other.supabase.co/auth/v1"}, private_key, algorithm="RS256", headers={"kid": "test-key"})
    wrong_audience = jwt.encode({**valid_claims, "aud": "other"}, private_key, algorithm="RS256", headers={"kid": "test-key"})

    for invalid in (expired, malformed, wrong_issuer, wrong_audience):
        with pytest.raises(InvalidAccessToken):
            verify_access_token(invalid, config)


def test_supabase_jwt_rejects_signature_forgery_and_unsupported_alg(monkeypatch):
    trusted = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeSigningKey:
        key = trusted.public_key()

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(auth, "_jwks_client", lambda _: FakeJwksClient())
    config = Settings(app_env="test", supabase_url="https://project.supabase.co")
    claims = {
        "sub": TEST_REPORTER_ID,
        "iss": config.supabase_issuer,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    forged = jwt.encode(claims, attacker, algorithm="RS256", headers={"kid": "test-key"})
    unsupported = jwt.encode(claims, "test-only-key-that-is-longer-than-thirty-two-bytes", algorithm="HS256")
    for token in (forged, unsupported):
        with pytest.raises(InvalidAccessToken):
            verify_access_token(token, config)


def test_report_service_binds_idempotency_to_owner(test_session_factory):
    payload = ReportCreate(
        id="ownership-idempotency",
        sector="Panambur",
        type="Turtle sighting",
        notes="Same report retry",
        timestamp="2026-10-24T12:00:00Z",
    )
    with test_session_factory() as session:
        created, is_new = create_or_get_report(session, payload, TEST_REPORTER_ID)
        retry, is_retry = create_or_get_report(session, payload, TEST_REPORTER_ID)
        assert created.id == retry.id and is_new and not is_retry
        with pytest.raises(ReportIdConflict):
            create_or_get_report(session, payload, str(uuid4()))
