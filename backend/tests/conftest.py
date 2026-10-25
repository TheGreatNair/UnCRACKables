from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth import AuthenticatedUser, get_current_user
from app.database import Base, build_engine, get_db_session
from app.main import app

TEST_REPORTER_ID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def test_session_factory(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield session_factory
    engine.dispose()


@pytest.fixture
def client(test_session_factory) -> Generator[TestClient, None, None]:
    def override_session():
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(TEST_REPORTER_ID)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def report_payload() -> dict:
    return {
        "id": "test-report-001",
        "sector": "Panambur",
        "type": "Turtle sighting",
        "notes": "Near the north end of the beach",
        "timestamp": "2026-10-24T12:00:00Z",
        "syncStatus": "pending",
        "reviewStatus": "not_reviewed",
    }
