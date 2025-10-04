# rag_agent/core/metrics.py
"""
Configuration for using backend metrics in rag_agent
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import metrics from backend
try:
    from app.core.metrics import record_prompt_version
except ImportError as e:
    # Use mock functions if backend is not available
    def record_prompt_version(version: str):
        """Mock function for prompt version recording"""
        pass

    print(f"Warning: Using mock metrics for rag_agent: {e}")

# Export record_prompt_version
__all__ = ["record_prompt_version"]
