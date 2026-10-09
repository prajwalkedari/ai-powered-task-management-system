"""Shared test setup.

Tests run against a dedicated PostgreSQL database (TEST_DATABASE_URL). Tables are recreated
for the session and truncated before every test, so the database name must contain 'test'.
Gemini is never called: AI tests inject a fake transport.
"""

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/task_manager_test",
)
if "test" not in TEST_DATABASE_URL.rsplit("/", 1)[-1].lower():
    raise RuntimeError("TEST_DATABASE_URL must point at a database whose name contains 'test'.")

# Set before any application module reads settings. Real .env values are overridden.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-longer-than-32-characters"
os.environ["GEMINI_API_KEY"] = ""

from app.auth.security import create_access_token, hash_password  # noqa: E402
from app.models import Base, Task, TaskStatus, User, UserRole  # noqa: E402

PASSWORD = "Correct-Horse-42"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    from app.database.session import get_engine

    db_engine = get_engine()
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    yield db_engine
    Base.metadata.drop_all(db_engine)
    db_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(engine: Engine) -> Iterator[None]:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE tasks, users RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    from app.database.session import get_db
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(db_session: Session) -> Callable[..., User]:
    def _create(email: str, *, role: UserRole = UserRole.USER, name: str = "Test User") -> User:
        user = User(name=name, email=email, password_hash=hash_password(PASSWORD), role=role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create


@pytest.fixture
def create_task(db_session: Session) -> Callable[..., Task]:
    def _create(
        owner: User,
        *,
        title: str = "Sample task",
        description: str | None = "Details",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        task = Task(user_id=owner.id, title=title, description=description, status=status)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    return _create


@pytest.fixture
def regular_user(create_user: Callable[..., User]) -> User:
    return create_user("alice@example.com", name="Alice")


@pytest.fixture
def other_user(create_user: Callable[..., User]) -> User:
    return create_user("bob@example.com", name="Bob")


@pytest.fixture
def admin_user(create_user: Callable[..., User]) -> User:
    return create_user("root@example.com", role=UserRole.ADMIN, name="Root Admin")


@pytest.fixture
def headers_for() -> Callable[[User], dict[str, str]]:
    def _headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id, user.role.value)
        return {"Authorization": f"Bearer {token}"}

    return _headers
