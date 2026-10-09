from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Task, TaskStatus, User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.permissions import ensure_task_access


def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    return task


def get_accessible_task(db: Session, user: User, task_id: int) -> Task:
    task = get_task_or_404(db, task_id)
    ensure_task_access(user, task)
    return task


def _scope_to_user(statement: Select, user: User) -> Select:
    # Non-admins are restricted in the query itself, so other users' rows are never loaded.
    if user.role != UserRole.ADMIN:
        statement = statement.where(Task.user_id == user.id)
    return statement


def list_tasks(
    db: Session,
    user: User,
    *,
    status: TaskStatus | None,
    skip: int,
    limit: int,
) -> tuple[list[Task], int]:
    count_stmt = _scope_to_user(select(func.count(Task.id)), user)
    items_stmt = _scope_to_user(select(Task), user)
    if status is not None:
        count_stmt = count_stmt.where(Task.status == status)
        items_stmt = items_stmt.where(Task.status == status)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(items_stmt.order_by(Task.id).offset(skip).limit(limit)).all()
    return list(items), int(total)


def create_task(db: Session, owner: User, payload: TaskCreate) -> Task:
    task = Task(
        user_id=owner.id,
        title=payload.title,
        description=payload.description,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    # exclude_unset: only fields the client actually sent are changed.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def update_task_status(db: Session, task: Task, status: TaskStatus) -> Task:
    task.status = status
    db.commit()
    db.refresh(task)
    return task
