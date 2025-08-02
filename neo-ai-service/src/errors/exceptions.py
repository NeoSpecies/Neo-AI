"""Custom exceptions for AI Service"""


class AIServiceError(Exception):
    """Base exception for AI Service"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ModelNotFoundError(AIServiceError):
    """Raised when requested model is not found"""
    def __init__(self, model: str, available_models: list = None):
        message = f"Model '{model}' not found"
        if available_models:
            message += f". Available models: {', '.join(available_models)}"
        super().__init__(
            message,
            error_code="MODEL_NOT_FOUND",
            details={"model": model, "available_models": available_models}
        )


class RateLimitError(AIServiceError):
    """Raised when rate limit is exceeded"""
    def __init__(self, client_id: str, wait_time: float = None, limit_type: str = None):
        message = f"Rate limit exceeded for client '{client_id}'"
        if wait_time:
            message += f". Retry after {wait_time:.1f} seconds"
        super().__init__(
            message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "client_id": client_id,
                "wait_time": wait_time,
                "limit_type": limit_type
            }
        )


class AdapterError(AIServiceError):
    """Raised when adapter encounters an error"""
    def __init__(self, adapter: str, message: str, original_error: Exception = None):
        super().__init__(
            f"Adapter '{adapter}' error: {message}",
            error_code="ADAPTER_ERROR",
            details={
                "adapter": adapter,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class ValidationError(AIServiceError):
    """Raised when request validation fails"""
    def __init__(self, field: str, message: str, value: any = None):
        super().__init__(
            f"Validation error for '{field}': {message}",
            error_code="VALIDATION_ERROR",
            details={
                "field": field,
                "value": value
            }
        )