from dataclasses import dataclass
from functools import lru_cache
import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from app.config import Settings, settings


logger = logging.getLogger("turtleway.security")


ALLOWED_JWT_ALGORITHMS = ("ES256", "RS256")
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationConfigurationError(Exception):
    pass


class AuthenticationProviderUnavailable(Exception):
    pass


class InvalidAccessToken(Exception):
    pass


@dataclass(frozen=True)
class AuthenticatedUser:
    subject: str


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=5)


def verify_access_token(token: str, config: Settings = settings) -> AuthenticatedUser:
    issuer = config.supabase_issuer
    jwks_url = config.supabase_jwks_url
    if not issuer or not jwks_url:
        raise AuthenticationConfigurationError

    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in ALLOWED_JWT_ALGORITHMS:
            raise InvalidAccessToken
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(ALLOWED_JWT_ALGORITHMS),
            issuer=issuer,
            audience=config.supabase_jwt_audience,
            options={"require": ["exp", "iss", "sub", "aud"]},
        )
    except PyJWKClientConnectionError as exc:
        raise AuthenticationProviderUnavailable from exc
    except (PyJWTError, ValueError, TypeError) as exc:
        raise InvalidAccessToken from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or len(subject) > 200:
        raise InvalidAccessToken
    try:
        normalized_subject = str(UUID(subject))
    except ValueError as exc:
        raise InvalidAccessToken from exc
    return AuthenticatedUser(subject=normalized_subject)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        logger.warning("Authentication rejected: bearer token missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "A valid bearer access token is required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_access_token(credentials.credentials)
    except AuthenticationConfigurationError as exc:
        logger.error("Authentication unavailable: Supabase verification configuration missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "authentication_not_configured", "message": "Authentication is temporarily unavailable."},
        ) from exc
    except AuthenticationProviderUnavailable as exc:
        logger.error("Authentication unavailable: Supabase signing-key endpoint unreachable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "authentication_provider_unavailable", "message": "Authentication is temporarily unavailable."},
        ) from exc
    except InvalidAccessToken as exc:
        logger.warning("Authentication rejected: token invalid or expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_access_token", "message": "The bearer access token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
