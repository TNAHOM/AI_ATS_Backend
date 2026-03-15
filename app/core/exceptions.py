from typing import Any


class BaseAppException(Exception):
    """Base exception for all standardized app-level errors."""

    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AIServiceError(Exception):
    """Base exception for AI Service errors."""
    pass


class AIParseError(AIServiceError):
    """Raised when AI returns invalid JSON or mismatched schema."""
    pass


class AIRateLimitError(AIServiceError):
    """Raised when API quota is exceeded."""
    pass


class AISafetyBlockedError(AIServiceError):
    """Raised when content is blocked by safety filters."""
    pass

class S3ServiceError(Exception):
    """Base exception for S3 storage errors"""
    pass