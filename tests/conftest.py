import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_vacation_planner.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("VECTOR_STORE_PROVIDER", "memory")
os.environ.setdefault("EMBEDDING_PROVIDER", "hash")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "claude-haiku-4-5")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.knowledge import KnowledgeDocument  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.trip import Trip  # noqa: F401
from app.models.itinerary import Itinerary  # noqa: F401


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_client(client):
    from uuid import uuid4
    from app.main import app
    from app.core.dependencies import get_current_user

    class FakeUser:
        id = uuid4()
        email = "tester@example.com"
        username = "tester"

    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
