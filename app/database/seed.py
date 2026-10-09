"""Development seeder: creates fixed development accounts and sample tasks.

Run after migrations:   python -m app.database.seed

Idempotent: existing accounts are left alone, and sample tasks are only added to
accounts that have none. DEVELOPMENT ONLY. These passwords are published in the README
and must never be used in a real deployment.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database.session import get_session_factory
from app.models import Task, TaskStatus, User, UserRole

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DevAccount:
    name: str
    email: str
    password: str
    role: UserRole


DEV_ACCOUNTS: tuple[DevAccount, ...] = (
    DevAccount("Dev Administrator", "admin@example.com", "Admin@12345", UserRole.ADMIN),
    DevAccount("Dev Standard User", "user@example.com", "User@12345", UserRole.USER),
    DevAccount("Dev Second User", "user2@example.com", "User2@12345", UserRole.USER),
)

SAMPLE_TASKS: dict[str, tuple[tuple[str, str, TaskStatus], ...]] = {
    "admin@example.com": (
        (
            "Review sprint backlog",
            "Prioritise open items for the next sprint and confirm owners.",
            TaskStatus.TESTING,
        ),
    ),
    "user@example.com": (
        (
            "Set up development environment",
            "Install Python, PostgreSQL and the project dependencies.",
            TaskStatus.COMPLETED,
        ),
        (
            "Implement login flow",
            "Connect the login form to the JWT authentication endpoint.",
            TaskStatus.IN_PROGRESS,
        ),
        (
            "Write API documentation",
            "Document the task endpoints with example requests and responses.",
            TaskStatus.PENDING,
        ),
    ),
    "user2@example.com": (
        (
            "Prepare release checklist",
            "List the steps required before the next release goes out.",
            TaskStatus.PENDING,
        ),
    ),
}


@dataclass
class SeedResult:
    users_created: int = 0
    tasks_created: int = 0
    messages: list[str] = field(default_factory=list)


def seed_database(db: Session) -> SeedResult:
    result = SeedResult()
    for account in DEV_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == account.email))
        if user is None:
            user = User(
                name=account.name,
                email=account.email,
                password_hash=hash_password(account.password),
                role=account.role,
            )
            db.add(user)
            db.flush()
            result.users_created += 1

        existing_tasks = db.scalar(select(func.count(Task.id)).where(Task.user_id == user.id)) or 0
        if existing_tasks == 0:
            for title, description, status in SAMPLE_TASKS.get(account.email, ()):
                db.add(Task(user_id=user.id, title=title, description=description, status=status))
                result.tasks_created += 1

    db.commit()
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with get_session_factory()() as db:
        result = seed_database(db)

    logger.info(
        "Seeding complete: %d user(s) created, %d task(s) created.",
        result.users_created,
        result.tasks_created,
    )
    logger.info("Development test accounts (DEVELOPMENT ONLY):")
    for account in DEV_ACCOUNTS:
        logger.info("  %-6s  %-18s  %s", account.role.value, account.email, account.password)


if __name__ == "__main__":
    main()
