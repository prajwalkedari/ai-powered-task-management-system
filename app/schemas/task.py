from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.enums import TaskStatus

TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
TaskDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class TaskCreate(BaseModel):
    # New tasks always start as Pending. Status cannot be set at creation.
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle = Field(examples=["Prepare sprint review"])
    description: TaskDescription | None = Field(default=None, examples=["Slides and metrics."])


class TaskUpdate(BaseModel):
    """Partial update of ordinary task fields. Status is deliberately absent: use the
    /status endpoint, which is admin-only. extra="forbid" makes a status field return 422."""

    model_config = ConfigDict(extra="forbid")

    title: TaskTitle | None = None
    description: TaskDescription | None = None

    @model_validator(mode="after")
    def check_update_payload(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null.")
        return self


class TaskStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TaskStatus = Field(examples=["In Progress"])


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int = Field(description="Total matching tasks, ignoring pagination")
    skip: int
    limit: int
