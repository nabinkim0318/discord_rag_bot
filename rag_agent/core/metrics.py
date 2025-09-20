# rag_agent/core/metrics.py
"""
Rag_agent에서 backend의 metrics를 사용하기 위한 설정
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# backend의 metrics를 import
try:
    from app.core.metrics import record_prompt_version
except ImportError as e:
    # backend가 없는 경우 mock 함수 사용
    def record_prompt_version(version: str):
        """Mock function for prompt version recording"""
        pass

    print(f"Warning: Using mock metrics for rag_agent: {e}")

# record_prompt_version을 export
__all__ = ["record_prompt_version"]
