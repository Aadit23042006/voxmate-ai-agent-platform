import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("GEMINI_API_KEY", "")


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    from app.database import Base, engine
    from app.models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    from app.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    import uuid
    from app.models.models import User

    # Bypasses hash_password (passlib/bcrypt) â€” these tests never log in,
    # they only need a real User row to satisfy foreign keys.
    user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password="test-password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

