"""Password hashing (Argon2id) and JWT access tokens (HS256 via PyJWT)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Return (token, lifetime_in_seconds). The role claim is informational only;
    authorisation always reloads the user from the database."""
    settings = get_settings()
    issued_at = datetime.now(timezone.utc)
    lifetime_seconds = settings.jwt_access_token_expire_minutes * 60
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=lifetime_seconds),
    }
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, lifetime_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature, algorithm and expiry. Raises jwt.InvalidTokenError on failure."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub"]},
    )
