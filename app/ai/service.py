"""Task AI features: prompts and output validation. HTTP lives in gemini_client."""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.exceptions import AIInvalidResponseError
from app.ai.gemini_client import GeminiClient
from app.ai.prompts import DESCRIPTION_PROMPT, SUMMARY_PROMPT
from app.ai.schemas import GeneratedDescription, GeneratedSummary

ModelT = TypeVar("ModelT", bound=BaseModel)


class TaskAIService:
    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    @property
    def model_name(self) -> str:
        return self._client.model

    def generate_description(self, title: str) -> str:
        raw = self._client.generate_json(
            DESCRIPTION_PROMPT.format(title=title), max_output_tokens=300
        )
        return _validate(GeneratedDescription, raw).description

    def summarize_task(self, title: str, description: str | None) -> str:
        prompt = SUMMARY_PROMPT.format(
            title=title, description=description or "(no description provided)"
        )
        raw = self._client.generate_json(prompt, max_output_tokens=200)
        return _validate(GeneratedSummary, raw).summary


def _validate(schema: type[ModelT], raw: dict) -> ModelT:
    try:
        return schema.model_validate(raw)
    except ValidationError as exc:
        raise AIInvalidResponseError() from exc
