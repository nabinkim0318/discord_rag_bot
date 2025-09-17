# app/core/error_handlers.py
"""
Centralized error handlers
"""


from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DatabaseException,
    ExternalServiceException,
    RAGException,
    ValidationException,
)
from app.core.logging import logger


def setup_error_handlers(app: FastAPI) -> None:
    """FastAPI app with error handlers"""

    @app.exception_handler(RAGException)
    async def rag_exception_handler(request: Request, exc: RAGException):
        logger.error(
            f"RAG Error: {exc.message}",
            extra={"error_code": exc.error_code, "details": exc.details},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "RAG Processing Error",
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        logger.error(
            f"Database Error: {exc.message}",
            extra={"error_code": exc.error_code, "details": exc.details},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database Error",
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        logger.warning(
            f"Validation Error: {exc.message}",
            extra={"error_code": exc.error_code, "details": exc.details},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(ExternalServiceException)
    async def external_service_exception_handler(
        request: Request, exc: ExternalServiceException
    ):
        logger.error(
            f"External Service Error ({exc.service_name}): {exc.message}",
            extra={
                "error_code": exc.error_code,
                "service": exc.service_name,
                "details": exc.details,
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "External Service Error",
                "message": exc.message,
                "error_code": exc.error_code,
                "service": exc.service_name,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled Error: {str(exc)}", extra={"exception_type": type(exc).__name__}
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "error_code": "INTERNAL_ERROR",
            },
        )
