# rag_agent/core/retry.py
"""
Configuration for using backend retry in rag_agent
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import retry from backend
try:
    from app.core.retry import retry_openai
except ImportError as e:
    # Use mock functions if backend is not available
    def retry_openai(max_attempts=3):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise e
                        print(f"Warning: Attempt {attempt + 1} failed: {e}")
                return None

            return wrapper

        return decorator

    print(f"Warning: Using mock retry for rag_agent: {e}")

# Export retry_openai
__all__ = ["retry_openai"]
