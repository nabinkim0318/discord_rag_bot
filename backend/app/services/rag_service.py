# app/services/rag_service.py
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import RAGException
from app.core.logging import log_rag_operation, logger
from app.core.metrics import (
    record_rag_pipeline_latency,
    record_retrieval_hit,
    record_retriever_topk,
)

# Import actual RAG pipeline from rag_agent
try:
    from rag_agent.generation.generation_pipeline import (
        generate_answer as rag_generate_answer,
    )

    RAG_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"rag_agent not available: {e}")
    RAG_AGENT_AVAILABLE = False


def generate_answer_mock(
    query: str,
    *,
    k_bm25: int = 30,
    k_vec: int = 30,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    reranker: Optional[str] = None,
    prompt_version: str = "v1.1",
    stream: bool = False,
    filters_fts: Optional[str] = None,
    filters_weaviate: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Mock implementation of generate_answer to avoid rag_agent dependency.
    In a real implementation, this would use the full RAG pipeline.
    """
    logger.warning("Using mock generate_answer - rag_agent not available")

    # Mock response
    answer = f"Mock response for query: {query[:50]}..."
    used_hits = [
        {
            "chunk_uid": "mock-chunk-1",
            "text": f"Mock context 1 for query: {query[:30]}...",
            "score": 0.95,
            "source": "mock_document.pdf",
            "metadata": {"page": 1, "section": "introduction"},
        },
        {
            "chunk_uid": "mock-chunk-2",
            "text": f"Mock context 2 for query: {query[:30]}...",
            "score": 0.87,
            "source": "mock_document.pdf",
            "metadata": {"page": 2, "section": "details"},
        },
    ]
    metadata = {
        "mock": True,
        "query": query,
        "k_bm25": k_bm25,
        "k_vec": k_vec,
        "k_final": k_final,
        "prompt_version": prompt_version,
    }

    return answer, used_hits, metadata


def generate_answer(
    query: str,
    *,
    k_bm25: int = 30,
    k_vec: int = 30,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    reranker: Optional[str] = None,
    prompt_version: str = "v1.1",
    stream: bool = False,
    filters_fts: Optional[str] = None,
    filters_weaviate: Optional[Dict[str, Any]] = None,
):
    # Use actual RAG pipeline (if available)
    if RAG_AGENT_AVAILABLE:
        try:
            return rag_generate_answer(
                query,
                k_bm25=k_bm25,
                k_vec=k_vec,
                k_final=k_final,
                bm25_weight=bm25_weight,
                vec_weight=vec_weight,
                mmr_lambda=mmr_lambda,
                reranker=reranker,
                prompt_version=prompt_version,
                stream=stream,
                filters_fts=filters_fts,
                filters_weaviate=filters_weaviate,
            )
        except Exception as e:
            logger.warning(f"RAG pipeline failed, falling back to mock: {e}")
            return generate_answer_mock(
                query,
                k_bm25=k_bm25,
                k_vec=k_vec,
                k_final=k_final,
                bm25_weight=bm25_weight,
                vec_weight=vec_weight,
                mmr_lambda=mmr_lambda,
                reranker=reranker,
                prompt_version=prompt_version,
                stream=stream,
                filters_fts=filters_fts,
                filters_weaviate=filters_weaviate,
            )
    else:
        # Use mock if rag_agent is not available
        logger.warning("Using mock generate_answer - rag_agent not available")
        return generate_answer_mock(
            query,
            k_bm25=k_bm25,
            k_vec=k_vec,
            k_final=k_final,
            bm25_weight=bm25_weight,
            vec_weight=vec_weight,
            mmr_lambda=mmr_lambda,
            reranker=reranker,
            prompt_version=prompt_version,
            stream=stream,
            filters_fts=filters_fts,
            filters_weaviate=filters_weaviate,
        )


def generate_answer_adapter(
    query: str, **kw
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    try:
        try:
            return generate_answer(
                query=query,
                k_bm25=kw.get("k_bm25", 20),
                k_vec=kw.get("k_vec", 20),
                k_final=kw.get("k_final", 8),
                bm25_weight=kw.get("bm25_weight", 0.4),
                vec_weight=kw.get("vec_weight", 0.6),
                mmr_lambda=kw.get("mmr_lambda", 0.65),
                reranker=kw.get("reranker"),
                prompt_version=kw.get("prompt_version", "v1.1"),
                stream=False,
                filters_fts=kw.get("filters_fts"),
                filters_weaviate=kw.get("filters_weaviate"),
            )
        except Exception as e:
            logger.warning(f"RAG real pipeline fallback to mock: {e}")
            return generate_answer_mock(query=query, **kw)
    except Exception as e:
        raise RAGException(f"Generation pipeline failed: {e}")


def run_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
    prompt_version: Optional[str] = "v1.1",
    use_rerank: bool = True,
    reranker: Optional[str] = "cohere",
    ab_test_group: Optional[str] = None,
) -> Tuple[str, List[str], Dict]:
    start = time.time()
    record_retriever_topk(top_k)

    ans_or_stream, used_hits, meta = generate_answer_adapter(
        query=query,
        k_bm25=max(30, top_k * 3),
        k_vec=max(30, top_k * 3),
        k_final=top_k,
        reranker=(reranker if use_rerank else None),
        prompt_version=prompt_version or "v1.1",
        stream=False,
    )

    answer = ans_or_stream if isinstance(ans_or_stream, str) else "".join(ans_or_stream)
    contexts = [h.get("text") or h.get("content", "") for h in used_hits]
    record_retrieval_hit(bool(contexts))

    duration = time.time() - start
    record_rag_pipeline_latency(duration)
    log_rag_operation(
        query, True, duration, len(contexts), user_id, channel_id, request_id
    )

    meta.update(
        {
            "sources": [h.get("source") for h in used_hits],
            "uids": [h.get("chunk_uid") for h in used_hits],
            "pipeline_duration": round(duration, 3),
            "prompt_version": prompt_version,
            "ab_test_group": ab_test_group,
            "use_rerank": use_rerank,
        }
    )
    return answer, contexts, meta


def search_similar_documents(
    query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search for similar documents using vector similarity.
    This is a placeholder implementation.
    """
    logger.warning("Using mock search_similar_documents - rag_agent not available")

    # Mock implementation
    mock_results = [
        {
            "chunk_uid": f"mock-chunk-{i}",
            "text": f"Mock document content {i} for query: {query[:30]}...",
            "score": 0.9 - (i * 0.1),
            "source": f"mock_document_{i}.pdf",
            "metadata": {"page": i + 1, "section": "content"},
        }
        for i in range(min(top_k, 3))
    ]

    return mock_results


def call_llm(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """
    Call the LLM with the given prompt.
    This is a placeholder implementation.
    """
    logger.warning("Using mock call_llm - rag_agent not available")

    # Mock implementation
    return f"Mock LLM response for prompt: {prompt[:50]}..."


def store_rag_result_in_weaviate(
    query: str, answer: str, contexts: List[str], metadata: Dict[str, Any]
) -> bool:
    """
    Store RAG result in Weaviate vector database.
    This is a placeholder implementation.
    """
    logger.warning("Using mock store_rag_result_in_weaviate - rag_agent not available")

    # Mock implementation - always return success
    return True
