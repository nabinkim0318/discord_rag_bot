# rag_agent/core/metrics.py
"""
Configuration for using backend metrics in rag_agent
"""
from ._bootstrap import attach_backend_path, get_fallback_logger

# Attach backend path
attach_backend_path()
logger = get_fallback_logger()

# Import metrics from backend
try:
    from app.core.metrics import record_prompt_version

    logger.info("Using backend metrics for rag_agent")
except Exception as e:
    # Use mock functions if backend is not available
    def record_prompt_version(version: str):
        """Mock function for prompt version recording"""
        pass

    logger.warning("Using mock metrics for rag_agent: %s", e)

# Export record_prompt_version
__all__ = ["record_prompt_version"]
