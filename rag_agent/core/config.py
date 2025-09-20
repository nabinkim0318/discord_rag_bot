# rag_agent/core/config.py
"""
Rag_agent에서 backend의 settings를 사용하기 위한 설정
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# backend의 settings를 import
try:
    from app.core.config import settings
except ImportError as e:
    # backend가 없는 경우 기본값 사용
    import os

    class MockSettings:
        """Mock settings for rag_agent when backend is not available"""

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
        AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        COHERE_API_KEY = os.getenv("COHERE_API_KEY")
        JINA_API_KEY = os.getenv("JINA_API_KEY")
        PROMPT_TOKEN_BUDGET = int(os.getenv("PROMPT_TOKEN_BUDGET", "4000"))
        GENERATION_MAX_TOKENS = int(os.getenv("GENERATION_MAX_TOKENS", "1000"))
        WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
        WEAVIATE_CLASS_NAME = os.getenv("WEAVIATE_CLASS_NAME", "RAGDocument")

    settings = MockSettings()
    print(f"Warning: Using mock settings for rag_agent: {e}")

# settings를 export
__all__ = ["settings"]
