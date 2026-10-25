import logging
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models import ReviewerScope, UserRole
from app.service import append_audit_event


logger = logging.getLogger("turtleway.security")


@dataclass(frozen=True)
class AccessContext:
    subject: str
    roles: frozenset[str]
    reviewer_sectors: frozenset[str]


def get_access_context(
    user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AccessContext:
    assigned_roles = set(session.scalars(
        select(UserRole.role).where(UserRole.subject == user.subject)
    ).all())
    assigned_roles.add("reporter")
    scopes = set(session.scalars(
        select(ReviewerScope.sector).where(ReviewerScope.subject == user.subject)
    ).all()) if "reviewer" in assigned_roles else set()
    return AccessContext(user.subject, frozenset(assigned_roles), frozenset(scopes))


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(
        request: Request,
        context: AccessContext = Depends(get_access_context),
        session: Session = Depends(get_db_session),
    ) -> AccessContext:
        if not context.roles.intersection(allowed_roles):
            logger.warning("Authorization denied for protected operation")
            append_audit_event(
                session,
                actor_subject=context.subject,
                action="authorization.denied",
                resource_type="api_operation",
                resource_id=f"{request.method} {request.url.path}"[:200],
                metadata={"requiredAnyOf": sorted(allowed_roles)},
            )
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                logger.error("Authorization denial could not be written to the audit log")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "insufficient_role", "message": "You are not authorized for this operation."},
            )
        return context

    return dependency
