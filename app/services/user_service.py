from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.core.exceptions import ConflictError
from app.models import User, UserRole

DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_user(db: Session, *, name: str, email: str, password: str) -> User:
    """Create a regular user. Role is always USER; it cannot be chosen at registration."""
    if get_user_by_email(db, email) is not None:
        raise ConflictError(DUPLICATE_EMAIL_MESSAGE)

    user = User(
        name=name.strip(),
        email=normalize_email(email),
        password_hash=hash_password(password),
        role=UserRole.USER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # Covers a race where two requests register the same email at once.
        db.rollback()
        raise ConflictError(DUPLICATE_EMAIL_MESSAGE) from exc
    db.refresh(user)
    return user


@lru_cache(maxsize=1)
def _timing_equalisation_hash() -> str:
    return hash_password("timing-equalisation-only")


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    """Return the user if the credentials match, otherwise None.
    Unknown emails still run one password verification so response timing does not reveal
    which emails are registered."""
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, _timing_equalisation_hash())
        return None
    return user if verify_password(password, user.password_hash) else None
