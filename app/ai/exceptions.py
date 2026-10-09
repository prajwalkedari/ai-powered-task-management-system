from app.core.exceptions import AppError


class AIServiceError(AppError):
    """Base for AI provider failures. Messages never expose provider details or keys."""

    status_code = 502
    error_code = "ai_provider_error"
    default_message = "The AI service could not complete the request. Please try again."


class AINotConfiguredError(AIServiceError):
    status_code = 503
    error_code = "ai_not_configured"
    default_message = "The AI service is not configured on this server."


class AITimeoutError(AIServiceError):
    status_code = 504
    error_code = "ai_timeout"
    default_message = "The AI service timed out. Please try again."


class AIInvalidResponseError(AIServiceError):
    status_code = 502
    error_code = "ai_invalid_response"
    default_message = "The AI service returned an unusable response. Please try again."
