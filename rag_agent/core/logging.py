# rag_agent/core/logging.py
"""
Configuration for using backend logging in rag_agent
"""

from ._bootstrap import attach_backend_path, get_fallback_logger

# Attach backend path
attach_backend_path()

# Try to import backend logger first
try:
    from app.core.logging import logger  # loguru logger
except Exception as e:
    logger = get_fallback_logger("rag_agent")
    logger.warning("Using basic logging for rag_agent: %s", e)

# Export logger
__all__ = ["logger"]
