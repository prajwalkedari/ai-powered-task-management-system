from typing import Annotated

from fastapi import Depends

from app.ai.gemini_client import GeminiClient
from app.ai.service import TaskAIService


def get_task_ai_service() -> TaskAIService:
    return TaskAIService(GeminiClient.from_settings())


TaskAIDep = Annotated[TaskAIService, Depends(get_task_ai_service)]
