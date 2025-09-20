# rag_agent/core/logging.py
"""
Rag_agent에서 backend의 logging을 사용하기 위한 설정
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# backend의 logging을 import
try:
    from app.core.logging import logger
except ImportError as e:
    # backend가 없는 경우 기본 logging 사용
    import logging

    logger = logging.getLogger("rag_agent")
    print(f"Warning: Using basic logging for rag_agent: {e}")

# logger를 export
__all__ = ["logger"]
