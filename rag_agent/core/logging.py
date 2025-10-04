# rag_agent/core/logging.py
"""
Configuration for using backend logging in rag_agent
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import logging from backend
try:
    from app.core.logging import logger
except ImportError as e:
    # Use basic logging if backend is not available
    import logging

    logger = logging.getLogger("rag_agent")
    print(f"Warning: Using basic logging for rag_agent: {e}")

# Export logger
__all__ = ["logger"]
