"""Application exceptions. Each carries an HTTP status, a stable error code and a safe message."""


class AppError(Exception):
    status_code: int = 500
    error_code: str = "internal_error"
    default_message: str = "An unexpected error occurred."
    headers: dict[str, str] | None = None

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"
    default_message = "Authentication is required."
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "The request conflicts with existing data."
