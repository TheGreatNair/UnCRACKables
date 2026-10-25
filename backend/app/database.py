from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    url = make_url(database_url)
    options: dict = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
    return create_engine(database_url, **options)


engine = build_engine(settings.sqlalchemy_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
