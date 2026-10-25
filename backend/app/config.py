from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'turtleway-dev.db').as_posix()}"
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    cors_origins: list[str] = ["http://localhost:19006", "http://localhost:8081", "http://localhost:5173"]
    log_level: str = "INFO"
    max_page_size: int = 100
    max_request_bytes: int = 1_048_576

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("sqlite:", "postgresql://", "postgresql+psycopg://", "postgres://")):
            raise ValueError("DATABASE_URL must use SQLite or PostgreSQL")
        return value

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("SUPABASE_URL must be an HTTP(S) project URL")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("SUPABASE_URL must be the project base URL")
        return value

    @field_validator("supabase_jwt_audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("SUPABASE_JWT_AUDIENCE cannot be empty")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, values: list[str]) -> list[str]:
        origins: list[str] = []
        for value in values:
            origin = value.strip().rstrip("/")
            parsed = urlsplit(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
            if parsed.path or parsed.query or parsed.fragment:
                raise ValueError("CORS_ORIGINS entries must be origins without paths or queries")
            origins.append(origin)
        return origins

    @model_validator(mode="after")
    def enforce_settings(self) -> "Settings":
        if not 1 <= self.max_page_size <= 500:
            raise ValueError("MAX_PAGE_SIZE must be between 1 and 500")
        if not 1_024 <= self.max_request_bytes <= 10_485_760:
            raise ValueError("MAX_REQUEST_BYTES must be between 1024 and 10485760")
        if self.app_env == "production":
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
                raise ValueError("Production requires a PostgreSQL DATABASE_URL; SQLite is not allowed")
            database_user = make_url(self.sqlalchemy_database_url).username or ""
            if database_user.split(".", 1)[0].lower() == "postgres":
                raise ValueError("Production requires a least-privilege application database role, not the postgres administrator role")
            if not self.supabase_url:
                raise ValueError("Production requires SUPABASE_URL for JWT issuer and signing-key verification")
            if urlsplit(self.supabase_url).scheme != "https":
                raise ValueError("Production SUPABASE_URL must use HTTPS")
            if not self.cors_origins or any(urlsplit(origin).scheme != "https" for origin in self.cors_origins):
                raise ValueError("Production requires explicit HTTPS CORS origins")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return "postgresql+psycopg://" + self.database_url.removeprefix("postgres://")
        if self.database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + self.database_url.removeprefix("postgresql://")
        return self.database_url

    @property
    def supabase_issuer(self) -> str | None:
        return f"{self.supabase_url}/auth/v1" if self.supabase_url else None

    @property
    def supabase_jwks_url(self) -> str | None:
        issuer = self.supabase_issuer
        return f"{issuer}/.well-known/jwks.json" if issuer else None


settings = Settings()


def ensure_api_access_policy(config: Settings = settings) -> None:
    if config.app_env == "production":
        if not config.supabase_url:
            raise RuntimeError("Production API startup requires Supabase Auth verification configuration")
        if config.sqlalchemy_database_url.startswith("sqlite:"):
            raise RuntimeError("Production API startup requires PostgreSQL")
        if not config.cors_origins or any(not origin.startswith("https://") for origin in config.cors_origins):
            raise RuntimeError("Production API startup requires explicit HTTPS CORS origins")
