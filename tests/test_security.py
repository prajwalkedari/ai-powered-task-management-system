from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth.security import create_access_token, hash_password, verify_password
from app.services.user_service import authenticate_user

SECRET = "test-only-secret-key-that-is-longer-than-32-characters"


def _token(claims: dict, *, key: str | None = SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(claims, key, algorithm=algorithm)


def _claims(user_id: int, *, expires_in: timedelta = timedelta(hours=1)) -> dict:
    now = datetime.now(timezone.utc)
    return {"sub": str(user_id), "role": "user", "iat": now, "exp": now + expires_in}


def test_password_hash_round_trip():
    stored = hash_password("pw-123456")
    assert stored != "pw-123456"
    assert verify_password("pw-123456", stored)
    assert not verify_password("wrong-password", stored)


def test_verify_password_returns_false_for_corrupt_hash():
    assert verify_password("anything", "not-a-real-hash") is False


def test_authenticate_user_returns_none_for_unknown_email(db_session):
    assert authenticate_user(db_session, email="ghost@example.com", password="whatever") is None


def test_expired_token_is_rejected(client, regular_user):
    token = _token(_claims(regular_user.id, expires_in=timedelta(hours=-1)))
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token has expired."


def test_token_signed_with_another_secret_is_rejected(client, regular_user):
    forged = _token(_claims(regular_user.id), key="attacker-secret-that-is-also-long-enough-1")
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid token."


def test_unsigned_alg_none_token_is_rejected(client, regular_user):
    forged = _token(_claims(regular_user.id), key=None, algorithm="none")
    response = client.get("/api/tasks", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_malformed_and_missing_credentials_are_rejected(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/tasks", headers={"Authorization": "Token abc"}).status_code == 401
    assert (
        client.get("/api/tasks", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401
    )


def test_token_for_deleted_user_is_rejected(client, db_session, create_user, headers_for):
    user = create_user("temporary@example.com")
    headers = headers_for(user)
    db_session.delete(user)
    db_session.commit()

    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_role_claim_in_token_is_not_trusted(client, regular_user, create_task):
    # The token claims role=admin, but authorisation uses the role stored in the database.
    task = create_task(regular_user)
    token, _ = create_access_token(regular_user.id, "admin")
    response = client.patch(
        f"/api/tasks/{task.id}/status",
        json={"status": "Completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("bad_secret", ["replace-with-something-random-and-long-enough", "short"])
def test_settings_reject_placeholder_or_short_jwt_secret(bad_secret):
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, database_url="postgresql+psycopg://x:y@h/db", jwt_secret_key=bad_secret
        )
