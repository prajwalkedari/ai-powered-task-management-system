from app.auth.security import decode_access_token

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
PASSWORD = "Correct-Horse-42"


def test_register_creates_regular_user_and_never_returns_password(client, db_session):
    response = client.post(
        REGISTER,
        json={"name": "Carol", "email": "Carol@Example.com", "password": "Sup3r-secret!"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "carol@example.com"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body

    from app.models import User

    stored = db_session.query(User).filter_by(email="carol@example.com").one()
    assert stored.password_hash != "Sup3r-secret!"
    assert stored.password_hash.startswith("$argon2")


def test_register_cannot_choose_a_role(client):
    response = client.post(
        REGISTER,
        json={
            "name": "Mallory",
            "email": "m@example.com",
            "password": "Sup3r-secret!",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_register_duplicate_email_is_rejected_case_insensitively(client, regular_user):
    response = client.post(
        REGISTER,
        json={"name": "Imposter", "email": "ALICE@example.com", "password": "Another-pass1"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_validates_input(client):
    invalid_payloads = [
        {"name": "X", "email": "not-an-email", "password": "long-enough-pw"},
        {"name": "X", "email": "x@example.com", "password": "short"},
        {"name": "   ", "email": "x@example.com", "password": "long-enough-pw"},
        {"name": "X", "email": "x@example.com"},
    ]
    for payload in invalid_payloads:
        assert client.post(REGISTER, json=payload).status_code == 422, payload


def test_login_returns_a_jwt_for_valid_credentials(client, regular_user):
    response = client.post(LOGIN, json={"email": "alice@example.com", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == str(regular_user.id)
    assert claims["role"] == "user"


def test_login_failures_are_indistinguishable(client, regular_user):
    wrong_password = client.post(
        LOGIN, json={"email": "alice@example.com", "password": "nope-nope"}
    )
    unknown_email = client.post(
        LOGIN, json={"email": "nobody@example.com", "password": "nope-nope"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "unauthorized"
    assert wrong_password.headers["www-authenticate"] == "Bearer"


def test_me_returns_the_authenticated_user(client, regular_user, headers_for):
    response = client.get("/api/auth/me", headers=headers_for(regular_user))
    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email


def test_me_requires_a_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
