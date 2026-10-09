from typing import Annotated

from fastapi import APIRouter, Query

from app.ai.dependencies import TaskAIDep
from app.auth.dependencies import AdminUser, CurrentUser
from app.database.session import DbSession
from app.models import TaskStatus
from app.schemas.ai import (
    GenerateDescriptionRequest,
    GenerateDescriptionResponse,
    SummarizeTaskResponse,
)
from app.schemas.common import error_responses
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    summary="Create a task owned by the caller",
    responses=error_responses(401, 422, 500),
)
def create_task(payload: TaskCreate, db: DbSession, current_user: CurrentUser) -> TaskRead:
    return task_service.create_task(db, current_user, payload)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks: own tasks for users, all tasks for admins",
    responses=error_responses(401, 422, 500),
)
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskListResponse:
    items, total = task_service.list_tasks(
        db, current_user, status=status_filter, skip=skip, limit=limit
    )
    return TaskListResponse(
        items=[TaskRead.model_validate(task) for task in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="View one task",
    responses=error_responses(401, 403, 404, 500),
)
def get_task(task_id: int, db: DbSession, current_user: CurrentUser) -> TaskRead:
    return task_service.get_accessible_task(db, current_user, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    summary="Edit title or description (owner or admin). Status cannot be changed here.",
    responses=error_responses(401, 403, 404, 422, 500),
)
def update_task(
    task_id: int, payload: TaskUpdate, db: DbSession, current_user: CurrentUser
) -> TaskRead:
    task = task_service.get_accessible_task(db, current_user, task_id)
    return task_service.update_task(db, task, payload)


@router.patch(
    "/{task_id}/status",
    response_model=TaskRead,
    summary="Update task status (administrators only)",
    responses=error_responses(401, 403, 404, 422, 500),
)
def update_task_status(
    task_id: int, payload: TaskStatusUpdate, db: DbSession, admin: AdminUser
) -> TaskRead:
    task = task_service.get_task_or_404(db, task_id)
    return task_service.update_task_status(db, task, payload.status)


@router.post(
    "/generate-description",
    response_model=GenerateDescriptionResponse,
    summary="AI: generate a task description from a title",
    responses=error_responses(401, 422, 500, 502, 503, 504),
)
def generate_description(
    payload: GenerateDescriptionRequest, ai: TaskAIDep, current_user: CurrentUser
) -> GenerateDescriptionResponse:
    description = ai.generate_description(payload.title)
    return GenerateDescriptionResponse(
        title=payload.title, description=description, model=ai.model_name
    )


@router.post(
    "/{task_id}/summarize",
    response_model=SummarizeTaskResponse,
    summary="AI: summarise a task using its title and description",
    responses=error_responses(401, 403, 404, 500, 502, 503, 504),
)
def summarize_task(
    task_id: int, db: DbSession, ai: TaskAIDep, current_user: CurrentUser
) -> SummarizeTaskResponse:
    task = task_service.get_accessible_task(db, current_user, task_id)
    summary = ai.summarize_task(task.title, task.description)
    return SummarizeTaskResponse(task_id=task.id, summary=summary, model=ai.model_name)
