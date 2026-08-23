# app/services/enhanced_rag_service.py
"""
Enhanced RAG service using rag_agent
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import ExternalServiceException, RAGException
from app.core.logging import log_rag_operation, logger
from app.core.metrics import (
    record_rag_pipeline_latency,
    record_rag_request,
    record_retrieval_hit,
)

# Try to import rag_agent components
try:
    from rag_agent.generation.generation_pipeline import generate_answer

    RAG_AGENT_AVAILABLE = True
    logger.info("Enhanced RAG: rag_agent available")
except ImportError as e:
    logger.warning(f"Enhanced RAG: rag_agent not available: {e}")
    RAG_AGENT_AVAILABLE = False

    def generate_answer(*args, **kwargs):
        raise RAGException(
            "RAG service is temporarily unavailable",
            error_code="RAG_DEPENDENCY_UNAVAILABLE",
            details={"stage": "initialization", "dependency": "rag_agent"},
        )


def run_enhanced_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Run enhanced RAG pipeline using actual RAG agent

    Args:
        query: User query
        top_k: Number of documents to retrieve
        user_id: User ID for tracking
        channel_id: Channel ID for context
        request_id: Request ID for tracking

    Returns:
        Tuple of (answer, contexts, metadata)
    """
    start_time = time.time()
    record_rag_request("/api/v1/enhanced-rag/")

    try:
        logger.info(f"Enhanced RAG: Processing query: {query[:100]}...")

        if not RAG_AGENT_AVAILABLE:
            raise RAGException(
                "RAG service is temporarily unavailable",
                error_code="RAG_DEPENDENCY_UNAVAILABLE",
                details={"stage": "initialization", "dependency": "rag_agent"},
            )

        ans_or_stream, used_hits, metadata = generate_answer(
            query=query,
            k_final=top_k,
            k_bm25=30,
            k_vec=30,
            bm25_weight=0.4,
            vec_weight=0.6,
            mmr_lambda=0.65,
            reranker=None,
            prompt_version="v1.1",
            stream=False,
        )

        answer = (
            ans_or_stream if isinstance(ans_or_stream, str) else "".join(ans_or_stream)
        )
        contexts = [h.get("text") or h.get("content", "") for h in used_hits]
        record_retrieval_hit(bool(contexts))

        total_time = time.time() - start_time
        enhanced_metadata = {
            "total_time": total_time,
            "user_id": user_id,
            "channel_id": channel_id,
            "request_id": request_id,
            "pipeline": "enhanced_rag",
            "rag_agent_available": True,
            "enhanced_rag": True,
            **metadata,
            "sources": [h.get("source") for h in used_hits],
            "uids": [h.get("chunk_uid") for h in used_hits],
        }

        record_rag_pipeline_latency(total_time)
        log_rag_operation(
            query,
            True,
            total_time,
            len(contexts),
            user_id,
            channel_id,
            request_id,
        )
        logger.info(
            f"Enhanced RAG completed in {total_time:.3f}s with {len(contexts)} contexts"
        )

        return answer, contexts, enhanced_metadata
    except (ExternalServiceException, RAGException):
        total_time = time.time() - start_time
        record_rag_pipeline_latency(total_time)
        log_rag_operation(query, False, total_time, 0, user_id, channel_id, request_id)
        raise
    except Exception as exc:
        total_time = time.time() - start_time
        record_rag_pipeline_latency(total_time)
        log_rag_operation(query, False, total_time, 0, user_id, channel_id, request_id)
        logger.exception("Enhanced RAG pipeline failed")
        raise RAGException(
            "RAG service is temporarily unavailable",
            error_code="ENHANCED_RAG_PIPELINE_ERROR",
            details={
                "stage": "enhanced_generation",
                "exception_type": type(exc).__name__,
            },
        ) from exc
