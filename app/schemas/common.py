from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Task not found."])
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


_ERROR_DESCRIPTIONS: dict[int, str] = {
    401: "Missing, invalid or expired bearer token",
    403: "Authenticated, but not permitted to perform this action",
    404: "Resource not found",
    409: "Conflicts with existing data",
    422: "Invalid request data",
    500: "Unexpected server or database error",
    502: "AI provider failed or returned an unusable response",
    503: "AI service is not configured on this server",
    504: "AI provider timed out",
}


def error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    """OpenAPI documentation for the error responses an endpoint can return."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }
