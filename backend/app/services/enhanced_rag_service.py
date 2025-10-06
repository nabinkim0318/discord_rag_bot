# app/services/enhanced_rag_service.py
"""
Enhanced RAG service using rag_agent
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.core.metrics import record_rag_request

# Try to import rag_agent components
try:
    from rag_agent.generation.generation_pipeline import generate_answer

    RAG_AGENT_AVAILABLE = True
    logger.info("Enhanced RAG: rag_agent available")
except ImportError as e:
    logger.warning(f"Enhanced RAG: rag_agent not available: {e}")
    RAG_AGENT_AVAILABLE = False

    # Create a dummy function for testing
    def generate_answer(*args, **kwargs):
        raise ImportError("RAG agent not available")


def run_enhanced_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Tuple[str, List[Dict], Dict[str, Any]]:
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

    try:
        logger.info(f"Enhanced RAG: Processing query: {query[:100]}...")

        # Record request metric
        record_rag_request("/api/v1/enhanced-rag/")

        if RAG_AGENT_AVAILABLE:
            try:
                # Use actual RAG pipeline
                answer, contexts, metadata = generate_answer(
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

                # Add enhanced metadata
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
                }

                logger.info(
                    f"Enhanced RAG completed in {total_time:.3f}s with {len(contexts)} contexts"
                )

                return answer, contexts, enhanced_metadata

            except Exception as e:
                logger.error(f"Enhanced RAG pipeline failed: {e}")
                # Fallback to simple response when RAG agent fails
                logger.warning("Enhanced RAG: RAG agent failed, using fallback")
                answer = f"Enhanced RAG failed. Query: {query}"
                contexts = []
                metadata = {
                    "total_time": time.time() - start_time,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "request_id": request_id,
                    "pipeline": "enhanced_rag_fallback",
                    "rag_agent_available": True,
                    "rag_agent_failed": True,
                    "enhanced_rag": True,
                    "error": str(e),
                }

                return answer, contexts, metadata

        else:
            # Fallback to simple response
            logger.warning("Enhanced RAG: rag_agent not available, using fallback")
            answer = f"Enhanced RAG is not available. Query: {query}"
            contexts = []
            metadata = {
                "total_time": time.time() - start_time,
                "user_id": user_id,
                "channel_id": channel_id,
                "request_id": request_id,
                "pipeline": "enhanced_rag_fallback",
                "rag_agent_available": False,
            }

            return answer, contexts, metadata

    except Exception as e:
        logger.exception(f"Enhanced RAG service failed: {e}")
        raise


def _mock_enhanced_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Tuple[str, List[Dict], Dict[str, Any]]:
    """
    Mock enhanced RAG pipeline for testing

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

    # Mock response
    answer = f"Mock enhanced RAG response for: {query}"
    contexts = [
        {
            "chunk_uid": "mock_chunk_1",
            "content": f"Mock context for: {query}",
            "source": "mock_source",
            "score": 0.95,
            "metadata": {"mock": True},
        }
    ]

    metadata = {
        "total_time": time.time() - start_time,
        "user_id": user_id,
        "channel_id": channel_id,
        "request_id": request_id,
        "pipeline": "mock_enhanced_rag",
        "rag_agent_available": False,
        "mock": True,
    }

    return answer, contexts, metadata
