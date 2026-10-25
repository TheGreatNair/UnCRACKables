import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.access import AccessContext, get_access_context, require_roles
from app.auth import AuthenticatedUser, get_current_user
from app.config import ensure_api_access_policy, settings
from app.database import engine, get_db_session
from app.models import AuditEvent, ReportRecord, ReviewerScope, UserRole
from app.risk import get_fishing_risk
from app.schemas import ReportCreate, ReviewStatus, ReviewUpdate
from app.service import ReportIdConflict, append_audit_event, create_or_get_report, response_payload
from app.turtleguard import router as turtleguard_router


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("turtleway.api")
REQUIRED_SCHEMA_REVISION = "0003_authz_audit"


class RequestBodyLimitMiddleware:
    """Enforce a bounded request body even when Content-Length is absent."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": {
                            "code": "request_too_large",
                            "message": "The request body exceeds the configured size limit.",
                        }
                    },
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        sent = False

        async def replay_body():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay_body, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_api_access_policy(settings)
    if settings.app_env == "production":
        try:
            with engine.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalar_one_or_none()
        except SQLAlchemyError:
            logger.error("Production database schema readiness check failed")
            raise RuntimeError("Production database schema is unavailable or not migrated") from None
        if revision != REQUIRED_SCHEMA_REVISION:
            raise RuntimeError("Production database must be migrated to the required application revision")
    logger.info("TurtleWay API starting in %s mode", settings.app_env)
    yield
    engine.dispose()


app = FastAPI(
    title="TurtleWay API",
    description="FastAPI backend for authenticated turtle conservation reporting",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(turtleguard_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        # Do not include exception text, request headers, tokens, or query values.
        logger.error("Request failed: %s %s", request.method, request.url.path)
        raise
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


def _api_error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _can_access_report(report: ReportRecord, access: AccessContext) -> bool:
    return (
        "administrator" in access.roles
        or report.reporter_subject == access.subject
        or ("reviewer" in access.roles and report.sector in access.reviewer_sectors)
    )


def _report_payload(report: ReportRecord, access: AccessContext) -> dict:
    return response_payload(
        report,
        include_review_notes=bool(access.roles.intersection({"reviewer", "administrator"})),
    )


@app.get("/health")
def health(session: Session = Depends(get_db_session)):
    """Public liveness/readiness check; exposes no database configuration."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Health check could not reach the configured database")
        raise _api_error("database_unavailable", "Database unavailable.", 503) from exc
    return {"status": "ok", "service": "TurtleWay API", "database": "ok"}


@app.get("/risk/fishing-activity")
def fishing_activity_risk():
    """Public read-only regional risk indicator from the bundled GFW snapshot."""
    return get_fishing_risk()


@app.post("/reports")
def receive_report(
    report: ReportCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    try:
        record, created = create_or_get_report(session, report, reporter_subject=user.subject)
    except ReportIdConflict as exc:
        raise _api_error(
            "report_id_conflict",
            "This report ID already exists with different data or ownership.",
            409,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Report persistence failed")
        raise _api_error("report_store_failed", "Could not store report.", 500) from exc

    report_body = response_payload(record)
    return {
        "success": True,
        "message": "Report received by TurtleWay server",
        "report": report_body,
        "receivedAt": report_body["receivedAt"],
        "duplicate": not created,
    }


@app.get("/reports")
def list_reports(
    limit: int = Query(default=50, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    sector: str | None = Query(default=None, max_length=120),
    review_status: ReviewStatus | None = Query(default=None, alias="reviewStatus"),
    access: AccessContext = Depends(get_access_context),
    session: Session = Depends(get_db_session),
):
    statement = select(ReportRecord)
    if "administrator" not in access.roles:
        visible = [ReportRecord.reporter_subject == access.subject]
        if "reviewer" in access.roles and access.reviewer_sectors:
            visible.append(ReportRecord.sector.in_(access.reviewer_sectors))
        statement = statement.where(or_(*visible))
    if sector is not None:
        statement = statement.where(ReportRecord.sector == sector)
    if review_status is not None:
        statement = statement.where(ReportRecord.review_status == review_status)
    if "administrator" in access.roles:
        append_audit_event(
            session,
            actor_subject=access.subject,
            action="reports.admin_list_read",
            resource_type="report_collection",
            resource_id="collection",
            metadata={"sectorFilter": sector, "reviewStatusFilter": review_status},
        )
        try:
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error("Administrator report-list audit write failed")
            raise _api_error("audit_write_failed", "Could not record privileged access.", 500) from exc
    try:
        records = session.scalars(
            statement.order_by(ReportRecord.received_at.desc(), ReportRecord.id.asc())
            .offset(offset)
            .limit(limit)
        ).all()
    except SQLAlchemyError as exc:
        logger.error("Report retrieval failed")
        raise _api_error("report_read_failed", "Could not read reports.", 500) from exc
    return [_report_payload(record, access) for record in records]


@app.get("/reports/{report_id}")
def get_report(
    report_id: str = Path(min_length=1, max_length=100),
    access: AccessContext = Depends(get_access_context),
    session: Session = Depends(get_db_session),
):
    record = session.get(ReportRecord, report_id)
    if record is None or not _can_access_report(record, access):
        raise _api_error("report_not_found", "Report not found.", 404)
    if "administrator" in access.roles:
        append_audit_event(
            session,
            actor_subject=access.subject,
            action="reports.admin_detail_read",
            resource_type="report",
            resource_id=record.id,
            metadata={},
        )
        try:
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error("Administrator report-read audit write failed")
            raise _api_error("audit_write_failed", "Could not record privileged access.", 500) from exc
    return _report_payload(record, access)


@app.patch("/reports/{report_id}/review")
def update_review(
    review: ReviewUpdate,
    report_id: str = Path(min_length=1, max_length=100),
    access: AccessContext = Depends(require_roles("reviewer", "administrator")),
    session: Session = Depends(get_db_session),
):
    record = session.get(ReportRecord, report_id)
    if record is None:
        raise _api_error("report_not_found", "Report not found.", 404)
    if "administrator" not in access.roles and record.sector not in access.reviewer_sectors:
        raise _api_error("report_not_found", "Report not found.", 404)

    target_status = review.review_status
    note_supplied = "review_notes" in review.model_fields_set
    target_notes = review.review_notes if note_supplied else record.review_notes
    changed_status = record.review_status != target_status
    changed_notes = record.review_notes != target_notes

    transitions = {
        "not_reviewed": {"in_review", "rejected"},
        "in_review": {"verified", "rejected"},
        "verified": set(),
        "rejected": set(),
    }
    if changed_status and target_status not in transitions.get(record.review_status, set()):
        raise _api_error(
            "invalid_review_transition",
            "The requested review status transition is not allowed.",
            409,
        )
    if not changed_status and not changed_notes:
        return {"success": True, "duplicate": True, "report": response_payload(record, include_review_notes=True)}
    if not changed_status and record.review_status != "in_review":
        raise _api_error(
            "invalid_review_transition",
            "Review notes can only be edited while a report is in review.",
            409,
        )

    previous_status = record.review_status
    record.review_status = target_status
    record.review_notes = target_notes
    record.reviewed_by = access.subject
    record.reviewed_at = datetime.now(timezone.utc)
    append_audit_event(
        session,
        actor_subject=access.subject,
        action="report.review_status_changed" if changed_status else "report.review_notes_changed",
        resource_type="report",
        resource_id=record.id,
        metadata={
            "previousStatus": previous_status,
            "newStatus": target_status,
            "reviewNotesChanged": changed_notes,
        },
    )
    try:
        session.commit()
        session.refresh(record)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Review update failed")
        raise _api_error("review_update_failed", "Could not update report review.", 500) from exc
    return {"success": True, "duplicate": False, "report": response_payload(record, include_review_notes=True)}


def _append_admin_read(session: Session, actor: str, action: str, resource: str) -> None:
    append_audit_event(
        session,
        actor_subject=actor,
        action=action,
        resource_type=resource,
        resource_id="collection",
        metadata={},
    )
    session.commit()


@app.get("/admin/reviewers")
def list_reviewer_scopes(
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    access: AccessContext = Depends(require_roles("administrator")),
    session: Session = Depends(get_db_session),
):
    _append_admin_read(session, access.subject, "reviewer_scopes.listed", "reviewer_scope")
    scopes = session.scalars(
        select(ReviewerScope).order_by(ReviewerScope.subject, ReviewerScope.sector).offset(offset).limit(limit)
    ).all()
    return [
        {"subject": item.subject, "sector": item.sector, "grantedBy": item.granted_by, "grantedAt": item.granted_at}
        for item in scopes
    ]


@app.put("/admin/reviewers/{subject}/sectors/{sector}")
def grant_reviewer_scope(
    subject: UUID,
    sector: str = Path(min_length=1, max_length=120),
    access: AccessContext = Depends(require_roles("administrator")),
    session: Session = Depends(get_db_session),
):
    normalized_subject = str(subject)
    normalized_sector = sector.strip()
    if not normalized_sector:
        raise _api_error("invalid_sector", "Sector cannot be blank.", 422)
    role = session.get(UserRole, (normalized_subject, "reviewer"))
    scope = session.get(ReviewerScope, (normalized_subject, normalized_sector))
    created = scope is None
    if role is None:
        session.add(UserRole(subject=normalized_subject, role="reviewer", granted_by=access.subject))
    if created:
        session.add(ReviewerScope(
            subject=normalized_subject,
            sector=normalized_sector,
            granted_by=access.subject,
        ))
    append_audit_event(
        session,
        actor_subject=access.subject,
        action="reviewer.scope_granted" if created else "reviewer.scope_grant_repeated",
        resource_type="reviewer_scope",
        resource_id=f"{normalized_subject}:{normalized_sector}",
        metadata={"sector": normalized_sector},
    )
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Reviewer scope grant failed")
        raise _api_error("reviewer_scope_update_failed", "Could not update reviewer access.", 500) from exc
    return {"success": True, "created": created, "subject": normalized_subject, "sector": normalized_sector}


@app.delete("/admin/reviewers/{subject}/sectors/{sector}")
def revoke_reviewer_scope(
    subject: UUID,
    sector: str = Path(min_length=1, max_length=120),
    access: AccessContext = Depends(require_roles("administrator")),
    session: Session = Depends(get_db_session),
):
    normalized_subject = str(subject)
    normalized_sector = sector.strip()
    scope = session.get(ReviewerScope, (normalized_subject, normalized_sector))
    if scope is None:
        raise _api_error("reviewer_scope_not_found", "Reviewer scope not found.", 404)
    session.delete(scope)
    remaining = session.scalar(
        select(ReviewerScope.subject)
        .where(
            ReviewerScope.subject == normalized_subject,
            ReviewerScope.sector != normalized_sector,
        )
        .limit(1)
    )
    if remaining is None:
        role = session.get(UserRole, (normalized_subject, "reviewer"))
        if role is not None:
            session.delete(role)
    append_audit_event(
        session,
        actor_subject=access.subject,
        action="reviewer.scope_revoked",
        resource_type="reviewer_scope",
        resource_id=f"{normalized_subject}:{normalized_sector}",
        metadata={"sector": normalized_sector, "reviewerRoleRemoved": remaining is None},
    )
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Reviewer scope revocation failed")
        raise _api_error("reviewer_scope_update_failed", "Could not update reviewer access.", 500) from exc
    return {"success": True, "revoked": True}


@app.get("/admin/audit")
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    actor_subject: str | None = Query(default=None, max_length=200),
    action: str | None = Query(default=None, max_length=80),
    access: AccessContext = Depends(require_roles("administrator")),
    session: Session = Depends(get_db_session),
):
    _append_admin_read(session, access.subject, "audit_events.listed", "audit_event")
    statement = select(AuditEvent)
    if actor_subject:
        statement = statement.where(AuditEvent.actor_subject == actor_subject)
    if action:
        statement = statement.where(AuditEvent.action == action)
    events = session.scalars(
        statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.asc()).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": event.id,
            "actorSubject": event.actor_subject,
            "action": event.action,
            "resourceType": event.resource_type,
            "resourceId": event.resource_id,
            "createdAt": event.created_at,
            "metadata": event.event_metadata,
        }
        for event in events
    ]
