# rag_agent/core/retry.py
"""
Configuration for using backend retry in rag_agent
"""

import asyncio
import inspect

from ._bootstrap import attach_backend_path, get_fallback_logger

# Attach backend path
attach_backend_path()
logger = get_fallback_logger()

# Import retry from backend
try:
    from app.core.retry import retry_openai

    logger.info("Using backend retry for rag_agent")
except Exception as e:
    # Use mock functions if backend is not available
    def retry_openai(max_attempts=3, base_delay=0.5):
        """Mock retry decorator with async support"""

        def decorator(func):
            if inspect.iscoroutinefunction(func):
                # Async function support
                async def async_wrapper(*args, **kwargs):
                    for attempt in range(max_attempts):
                        try:
                            return await func(*args, **kwargs)
                        except Exception as ex:
                            if attempt == max_attempts - 1:
                                raise ex
                            delay = base_delay * (2**attempt)
                            logger.warning(
                                "Attempt %d failed, retrying in %.2fs: %s",
                                attempt + 1,
                                delay,
                                ex,
                            )
                            await asyncio.sleep(delay)
                    return None

                return async_wrapper
            else:
                # Sync function support
                def sync_wrapper(*args, **kwargs):
                    for attempt in range(max_attempts):
                        try:
                            return func(*args, **kwargs)
                        except Exception as ex:
                            if attempt == max_attempts - 1:
                                raise ex
                            delay = base_delay * (2**attempt)
                            logger.warning(
                                "Attempt %d failed, retrying in %.2fs: %s",
                                attempt + 1,
                                delay,
                                ex,
                            )
                            asyncio.run(asyncio.sleep(delay))
                    return None

                return sync_wrapper

        return decorator

    logger.warning("Using mock retry for rag_agent: %s", e)

# Export retry_openai
__all__ = ["retry_openai"]
