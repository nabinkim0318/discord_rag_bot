# app/core/error_handlers.py
"""
Centralized error handlers with enhanced error responses
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    DatabaseException,
    ExternalServiceException,
    RAGException,
    ValidationException,
)
from app.core.logging import logger
from app.models.error import (
    ErrorDetail,
    create_circuit_breaker_error,
    create_database_error,
    create_rag_error,
    create_rate_limit_error,
    create_service_error,
    create_validation_error,
)


def get_request_id(request: Request) -> str:
    """Extract request ID from headers or generate one"""
    return request.headers.get("X-Request-ID", "unknown")


def setup_error_handlers(app: FastAPI) -> None:
    """FastAPI app with enhanced error handlers"""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI validation errors"""
        request_id = get_request_id(request)

        details = []
        for error in exc.errors():
            details.append(
                ErrorDetail(
                    field=".".join(str(loc) for loc in error["loc"]),
                    message=error["msg"],
                    code=error["type"],
                    value=error.get("input"),
                )
            )

        error_response = create_validation_error(
            message="Request validation failed", details=details, request_id=request_id
        )

        logger.warning(
            f"Validation Error: {exc}",
            extra={"request_id": request_id, "details": details},
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        request_id = get_request_id(request)

        # Handle rate limiting
        if exc.status_code == 429:
            retry_after = int(exc.headers.get("Retry-After", 60))
            error_response = create_rate_limit_error(
                retry_after=retry_after, request_id=request_id
            )
            return JSONResponse(
                status_code=429,
                content=error_response.dict(),
                headers={"Retry-After": str(retry_after)},
            )

        # Handle circuit breaker
        if exc.status_code == 503 and "circuit breaker" in str(exc.detail).lower():
            error_response = create_circuit_breaker_error(
                service="unknown", state="open", retry_after=60, request_id=request_id
            )
            return JSONResponse(
                status_code=503,
                content=error_response.dict(),
                headers={"Retry-After": "60"},
            )

        logger.warning(
            f"HTTP Error {exc.status_code}: {exc.detail}",
            extra={"request_id": request_id},
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": "HTTP Error",
                "error_code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(RAGException)
    async def rag_exception_handler(request: Request, exc: RAGException):
        """Handle RAG pipeline errors"""
        request_id = get_request_id(request)

        error_response = create_rag_error(
            message=exc.message, stage=exc.details.get("stage"), request_id=request_id
        )

        logger.error(
            f"RAG Error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": request_id,
            },
        )

        return JSONResponse(status_code=500, content=error_response.model_dump())

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        """Handle database errors"""
        request_id = get_request_id(request)

        error_response = create_database_error(
            message=exc.message, request_id=request_id
        )

        logger.error(
            f"Database Error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": request_id,
            },
        )

        return JSONResponse(status_code=500, content=error_response.model_dump())

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """Handle validation errors"""
        request_id = get_request_id(request)

        error_response = create_validation_error(
            message=exc.message, request_id=request_id
        )

        logger.warning(
            f"Validation Error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": request_id,
            },
        )

        return JSONResponse(status_code=422, content=error_response.model_dump())

    @app.exception_handler(ExternalServiceException)
    async def external_service_exception_handler(
        request: Request, exc: ExternalServiceException
    ):
        """Handle external service errors"""
        request_id = get_request_id(request)

        # Check if it's a circuit breaker error
        if "circuit breaker" in exc.message.lower():
            error_response = create_circuit_breaker_error(
                service=exc.service_name,
                state="open",
                retry_after=60,
                request_id=request_id,
            )
            status_code = 503
            headers = {"Retry-After": "60"}
        else:
            error_response = create_service_error(
                message=exc.message,
                service=exc.service_name,
                retry_after=30,
                request_id=request_id,
            )
            status_code = 503
            headers = {"Retry-After": "30"}

        logger.error(
            f"External Service Error ({exc.service_name}): {exc.message}",
            extra={
                "error_code": exc.error_code,
                "service": exc.service_name,
                "details": exc.details,
                "request_id": request_id,
            },
        )

        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors"""
        request_id = get_request_id(request)

        logger.error(
            f"Unhandled Error: {str(exc)}",
            extra={"exception_type": type(exc).__name__, "request_id": request_id},
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal Server Error",
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            },
        )
