"""
Bootstrap utilities for rag_agent
- Backend path injection with ENV support
- Fallback logging configuration
- Common utilities for rag_agent modules
"""

import logging
import os
import sys
from pathlib import Path


def attach_backend_path():
    """
    Attach backend directory to sys.path with ENV priority

    Returns:
        Path: Resolved backend path
    """
    backend_env = os.getenv("BACKEND_PATH")
    if backend_env:
        p = Path(backend_env).resolve()
    else:
        # Default: go up 2 levels from current file, then into backend
        p = (Path(__file__).parents[2] / "backend").resolve()

    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

    return p


def get_fallback_logger(name="rag_agent"):
    """
    Get fallback logger with basic configuration

    Args:
        name: Logger name

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Configure basic logging if no handlers exist
        log_level = os.getenv("LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    return logger


def get_backend_settings():
    """
    Try to import backend settings with fallback

    Returns:
        settings object or None
    """
    try:
        from app.core.config import settings

        return settings
    except Exception:
        return None


def get_backend_logger():
    """
    Try to import backend logger with fallback

    Returns:
        logger object or None
    """
    try:
        from app.core.logging import logger

        return logger
    except Exception:
        return None


def get_backend_metrics():
    """
    Try to import backend metrics with fallback

    Returns:
        metrics object or None
    """
    try:
        from app.core.metrics import record_prompt_version

        return {"record_prompt_version": record_prompt_version}
    except Exception:
        return None


def get_backend_retry():
    """
    Try to import backend retry with fallback

    Returns:
        retry function or None
    """
    try:
        from app.core.retry import retry_openai

        return retry_openai
    except Exception:
        return None
