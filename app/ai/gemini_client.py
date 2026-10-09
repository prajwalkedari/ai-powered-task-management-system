"""Minimal client for Google Gemini's generateContent REST endpoint.

All HTTP and provider-specific parsing lives here. Callers receive a parsed JSON object,
or an AIServiceError subclass. The API key is sent in a header and never logged."""

import json
import logging
from typing import Any

import httpx

from app.ai.exceptions import (
    AIInvalidResponseError,
    AINotConfiguredError,
    AIServiceError,
    AITimeoutError,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._endpoint = f"{base_url.rstrip('/')}/models/{model}:generateContent"
        self._timeout = timeout_seconds
        # Injectable transport lets tests replace the network with httpx.MockTransport.
        self._transport = transport

    @classmethod
    def from_settings(cls) -> "GeminiClient":
        settings = get_settings()
        return cls(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            timeout_seconds=settings.gemini_timeout_seconds,
        )

    def generate_json(self, prompt: str, *, max_output_tokens: int) -> dict[str, Any]:
        """Send a prompt and return the model's JSON object. Raises AIServiceError subclasses."""
        if not self._api_key:
            raise AINotConfiguredError()

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4,
                "maxOutputTokens": max_output_tokens,
            },
        }
        headers = {"x-goog-api-key": self._api_key}

        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as http:
                response = http.post(self._endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            logger.warning("Gemini request timed out after %s seconds", self._timeout)
            raise AITimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini request failed: %s", type(exc).__name__)
            raise AIServiceError() from exc

        if response.status_code != 200:
            logger.error("Gemini responded with HTTP %s", response.status_code)
            raise AIServiceError()

        return _parse_generate_content(response)


def _parse_generate_content(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise AIInvalidResponseError() from exc
    if not isinstance(body, dict):
        raise AIInvalidResponseError()

    feedback = body.get("promptFeedback")
    if isinstance(feedback, dict) and feedback.get("blockReason"):
        logger.warning("Gemini blocked the prompt: %s", feedback.get("blockReason"))
        raise AIInvalidResponseError("The AI service declined to process this request.")

    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise AIInvalidResponseError()

    content = candidates[0].get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise AIInvalidResponseError()

    text = "".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not text:
        raise AIInvalidResponseError()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIInvalidResponseError() from exc
    if not isinstance(parsed, dict):
        raise AIInvalidResponseError()
    return parsed
