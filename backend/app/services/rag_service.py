# 예시: backend/app/services/rag_service.py

from app.core.logging import logger


def run_rag_pipeline(query: str):
    logger.info(f"Received query: {query}")
    try:
        # Your pipeline logic
        ...
        logger.debug("Pipeline finished successfully")
        return "result"
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        raise
