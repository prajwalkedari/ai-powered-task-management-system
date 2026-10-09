from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import TaskTitle


class GenerateDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle = Field(examples=["Migrate login page to OAuth"])


class GenerateDescriptionResponse(BaseModel):
    title: str
    description: str
    model: str = Field(description="Gemini model that produced the text")


class SummarizeTaskResponse(BaseModel):
    task_id: int
    summary: str
    model: str = Field(description="Gemini model that produced the text")
