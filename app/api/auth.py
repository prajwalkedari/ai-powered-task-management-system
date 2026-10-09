from fastapi import APIRouter, status

from app.auth.dependencies import CurrentUser
from app.auth.security import create_access_token
from app.core.exceptions import UnauthorizedError
from app.database.session import DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import error_responses
from app.schemas.user import UserRead
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses=error_responses(409, 422, 500),
)
def register(payload: RegisterRequest, db: DbSession) -> UserRead:
    return user_service.register_user(
        db, name=payload.name, email=payload.email, password=payload.password
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
    responses=error_responses(401, 422, 500),
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = user_service.authenticate_user(db, email=payload.email, password=payload.password)
    if user is None:
        raise UnauthorizedError("Invalid email or password.")
    token, expires_in = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated user",
    responses=error_responses(401, 500),
)
def read_current_user(current_user: CurrentUser) -> UserRead:
    return current_user
