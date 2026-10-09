"""Central place for task-level access rules. Every task read or write goes through here."""

from app.core.exceptions import ForbiddenError
from app.models import Task, User, UserRole


def can_access_task(user: User, task: Task) -> bool:
    """Admins may access any task. Regular users may access only tasks they own."""
    return user.role == UserRole.ADMIN or task.user_id == user.id


def ensure_task_access(user: User, task: Task) -> None:
    if not can_access_task(user, task):
        raise ForbiddenError("You do not have access to this task.")
