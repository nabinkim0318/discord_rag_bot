# rag_agent/core/retry.py
"""
Rag_agent에서 backend의 retry를 사용하기 위한 설정
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# backend의 retry를 import
try:
    from app.core.retry import retry_openai
except ImportError as e:
    # backend가 없는 경우 mock 함수 사용
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

# retry_openai를 export
__all__ = ["retry_openai"]
