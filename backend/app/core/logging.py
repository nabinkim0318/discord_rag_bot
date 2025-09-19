# backend/app/core/logging.py

import sys
from typing import Optional

from loguru import logger

from app.core.config import settings

LOG_DIR = settings.LOG_DIR
LOG_DIR.mkdir(parents=True, exist_ok=True)  # create logs directory

# default logging settings
logger.remove()  # remove default handler (disable FastAPI default logger)

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
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs,
):
    """API request logging"""
    logger.bind(
        api_request=True, request_id=request_id, user_id=user_id, channel_id=channel_id
    ).info(
        f"API Request: {method} {path} | Status: {status_code} \
        | Duration: {duration:.3f}s \
        | User: {user_id} | Channel: {channel_id} | RequestID: {request_id}",
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
    query: str,
    success: bool,
    duration: Optional[float] = None,
    contexts_count: Optional[int] = None,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs,
):
    """RAG operation logging"""
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" | Duration: {duration:.3f}s" if duration else ""
    contexts_str = f" | Contexts: {contexts_count}" if contexts_count else ""
    logger.bind(request_id=request_id, user_id=user_id, channel_id=channel_id).info(
        f"RAG Query: '{query[:50]}...' | Status: {status}{duration_str}{contexts_str} \
        | User: {user_id} | Channel: {channel_id} | RequestID: {request_id}",
        **kwargs,
    )
