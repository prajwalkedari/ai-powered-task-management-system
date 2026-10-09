"""Error envelope, documentation endpoints, seeder and migration-independent behaviour."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.seed import DEV_ACCOUNTS, seed_database
from app.main import app
from app.models import Task, User, UserRole


def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_openapi_documents_every_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/auth/register" in paths
    assert "/api/auth/login" in paths
    assert "/api/tasks" in paths
    assert "/api/tasks/{task_id}/status" in paths
    assert "/api/tasks/generate-description" in paths
    assert "/api/tasks/{task_id}/summarize" in paths
    assert client.get("/docs").status_code == 200


def test_unknown_route_uses_the_error_envelope(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_errors_do_not_echo_submitted_values(client):
    response = client.post(
        "/api/auth/register", json={"name": "A", "email": "bad-email", "password": "hunter2"}
    )
    assert response.status_code == 422
    assert "hunter2" not in response.text


def test_database_errors_are_sanitised(client, regular_user, headers_for, monkeypatch):
    from app.services import task_service

    def broken(*args, **kwargs):
        raise SQLAlchemyError("relation secret_internal_table does not exist")

    monkeypatch.setattr(task_service, "list_tasks", broken)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/api/tasks", headers=headers_for(regular_user))

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "database_error"
    assert "secret_internal_table" not in response.text


def test_unexpected_errors_return_generic_500(client, regular_user, headers_for, monkeypatch):
    from app.services import task_service

    def broken(*args, **kwargs):
        raise RuntimeError("password=supersecret")

    monkeypatch.setattr(task_service, "list_tasks", broken)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/api/tasks", headers=headers_for(regular_user))

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "supersecret" not in response.text


def test_seeder_creates_accounts_and_sample_tasks(db_session):
    result = seed_database(db_session)

    assert result.users_created == len(DEV_ACCOUNTS)
    assert result.tasks_created > 0
    admin = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert admin.role == UserRole.ADMIN
    assert admin.password_hash.startswith("$argon2")


def test_seeder_is_idempotent(db_session):
    seed_database(db_session)
    second_run = seed_database(db_session)

    assert second_run.users_created == 0
    assert second_run.tasks_created == 0
    assert db_session.scalar(select(func.count(User.id))) == len(DEV_ACCOUNTS)
    assert db_session.scalar(select(func.count(Task.id))) > 0
