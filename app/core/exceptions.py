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