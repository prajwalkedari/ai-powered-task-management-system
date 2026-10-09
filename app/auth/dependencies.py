"""FastAPI dependencies that authenticate the caller and enforce roles."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.database.session import DbSession
from app.models import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token.") from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token.") from exc

    # Reload the user on every request so deleted accounts and role changes take effect at once.
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Invalid token.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Administrator privileges are required for this action.")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
