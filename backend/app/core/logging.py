# backend/app/core/logging.py

import sys
from typing import Optional

from loguru import logger

from app.core.config import settings

LOG_DIR = settings.LOG_DIR
LOG_DIR.mkdir(parents=True, exist_ok=True)  # create logs directory

# default logging settings
logger.remove()  # Remove Loguru's default console handler to avoid duplicate logs

# Console logging
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    enqueue=True,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "{message}",
)

# General application logs
logger.add(
    LOG_DIR / "app.log",
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level=settings.LOG_LEVEL,
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | \
    {name}:{function}:{line} | {message}",
)

# Error logs (ERROR and above)
logger.add(
    LOG_DIR / "error.log",
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level="ERROR",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | \
    {name}:{function}:{line} | {message}",
)

# API request logs
logger.add(
    LOG_DIR / "api.log",
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level="INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | \
    {message}",
    filter=lambda record: "api_request" in record["extra"],
)

# Database operation logs
logger.add(
    LOG_DIR / "database.log",
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level="INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | \
    {message}",
    filter=lambda record: "db_operation" in record["extra"],
)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None,
    **kwargs,
):
    """API request logging without user content or identity fields."""
    logger.bind(api_request=True, request_id=request_id).info(
        f"API Request: {method} {path} | Status: {status_code} "
        f"| Duration: {duration:.3f}s | RequestID: {request_id}",
        **kwargs,
    )


def log_database_operation(
    operation: str,
    table: str,
    success: bool,
    duration: Optional[float] = None,
    **kwargs,
):
    """Database operation logging"""
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" | Duration: {duration:.3f}s" if duration else ""
    logger.bind(db_operation=True).info(
        f"DB {operation}: {table} | Status: {status}{duration_str}",
        **kwargs,
    )


def log_rag_operation(
    *,
    success: bool,
    duration: Optional[float] = None,
    contexts_count: Optional[int] = None,
    request_id: Optional[str] = None,
    query_length: Optional[int] = None,
    endpoint: Optional[str] = None,
    **kwargs,
):
    """RAG operation logging without query text or user/channel identifiers."""
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" | Duration: {duration:.3f}s" if duration else ""
    contexts_str = (
        f" | Contexts: {contexts_count}" if contexts_count is not None else ""
    )
    length_str = f" | QueryLength: {query_length}" if query_length is not None else ""
    endpoint_str = f" | Endpoint: {endpoint}" if endpoint else ""
    logger.bind(request_id=request_id).info(
        f"RAG Query: Status: {status}{duration_str}{contexts_str}{length_str}"
        f"{endpoint_str} | RequestID: {request_id}",
        **kwargs,
    )
