import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.config import USERNAME, PASSWORD
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _make_test_client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Deliberately NOT using `with TestClient(app) as c:` — entering the
    # context manager fires the app's lifespan startup logic, which
    # calls Base.metadata.create_all() against the PRODUCTION engine
    # (app.database.engine), not this test's in-memory one. Plain
    # construction skips startup/shutdown entirely, which is fine because
    # this fixture already creates tables on the test engine directly.
    return TestClient(app)


@pytest.fixture()
def anon_client(db_engine):
    """A client with no session — for testing the login-required behavior itself."""
    test_client = _make_test_client(db_engine)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db_engine):
    """A client that's already logged in — every other test uses this."""
    test_client = _make_test_client(db_engine)
    test_client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
