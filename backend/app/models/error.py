# app/models/error.py
"""
Error response models for consistent API error handling
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_serializer


class ErrorDetail(BaseModel):
    """Detailed error information"""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None
    value: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standardized error response format"""

    success: bool = False
    error: str
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    service: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()

    class Config:
        from_attributes = True


class ValidationErrorResponse(ErrorResponse):
    """Validation error response"""

    error: str = "Validation Error"
    error_code: str = "VALIDATION_ERROR"


class ServiceErrorResponse(ErrorResponse):
    """External service error response"""

    error: str = "Service Error"
    error_code: str = "SERVICE_ERROR"
    service: str
    retry_after: Optional[int] = None


class DatabaseErrorResponse(ErrorResponse):
    """Database error response"""

    error: str = "Database Error"
    error_code: str = "DATABASE_ERROR"


class RAGErrorResponse(ErrorResponse):
    """RAG pipeline error response"""

    error: str = "RAG Pipeline Error"
    error_code: str = "RAG_ERROR"
    stage: Optional[str] = None  # Which stage of RAG pipeline failed


class RateLimitErrorResponse(ErrorResponse):
    """Rate limit error response"""

    error: str = "Rate Limit Exceeded"
    error_code: str = "RATE_LIMIT_ERROR"
    retry_after: int
    limit: Optional[int] = None
    remaining: Optional[int] = None


class CircuitBreakerErrorResponse(ErrorResponse):
    """Circuit breaker error response"""

    error: str = "Service Temporarily Unavailable"
    error_code: str = "CIRCUIT_BREAKER_OPEN"
    service: str
    retry_after: int
    state: str  # "open", "half_open"


# Error response factory functions
def create_validation_error(
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None,
) -> ValidationErrorResponse:
    """Create validation error response"""
    return ValidationErrorResponse(
        message=message, details=details, request_id=request_id
    )


def create_service_error(
    message: str,
    service: str,
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None,
) -> ServiceErrorResponse:
    """Create service error response"""
    return ServiceErrorResponse(
        message=message, service=service, retry_after=retry_after, request_id=request_id
    )


def create_database_error(
    message: str, request_id: Optional[str] = None
) -> DatabaseErrorResponse:
    """Create database error response"""
    return DatabaseErrorResponse(message=message, request_id=request_id)


def create_rag_error(
    message: str, stage: Optional[str] = None, request_id: Optional[str] = None
) -> RAGErrorResponse:
    """Create RAG pipeline error response"""
    return RAGErrorResponse(message=message, stage=stage, request_id=request_id)


def create_rate_limit_error(
    retry_after: int,
    limit: Optional[int] = None,
    remaining: Optional[int] = None,
    request_id: Optional[str] = None,
) -> RateLimitErrorResponse:
    """Create rate limit error response"""
    return RateLimitErrorResponse(
        message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        retry_after=retry_after,
        limit=limit,
        remaining=remaining,
        request_id=request_id,
    )


def create_circuit_breaker_error(
    service: str, state: str, retry_after: int, request_id: Optional[str] = None
) -> CircuitBreakerErrorResponse:
    """Create circuit breaker error response"""
    return CircuitBreakerErrorResponse(
        message=f"Service '{service}' is temporarily unavailable (state: {state})",
        service=service,
        retry_after=retry_after,
        state=state,
        request_id=request_id,
    )
