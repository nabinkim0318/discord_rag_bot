# app/services/rag_service.py
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import ExternalServiceException, RAGException
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
    if not RAG_AGENT_AVAILABLE:
        raise RAGException(
            "RAG service is temporarily unavailable",
            error_code="RAG_DEPENDENCY_UNAVAILABLE",
            details={"stage": "initialization", "dependency": "rag_agent"},
        )

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
    except (ExternalServiceException, RAGException):
        raise
    except Exception as exc:
        logger.exception("RAG generation pipeline failed")
        raise RAGException(
            "RAG service is temporarily unavailable",
            error_code="RAG_GENERATION_ERROR",
            details={"stage": "generation", "exception_type": type(exc).__name__},
        ) from exc


def generate_answer_adapter(
    query: str, **kw
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
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
    except (ExternalServiceException, RAGException):
        raise
    except Exception as exc:
        logger.exception("RAG generation adapter failed")
        raise RAGException(
            "RAG service is temporarily unavailable",
            error_code="RAG_PIPELINE_ERROR",
            details={"stage": "generation", "exception_type": type(exc).__name__},
        ) from exc


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

    try:
        ans_or_stream, used_hits, meta = generate_answer_adapter(
            query=query,
            k_bm25=max(30, top_k * 3),
            k_vec=max(30, top_k * 3),
            k_final=top_k,
            reranker=(reranker if use_rerank else None),
            prompt_version=prompt_version or "v1.1",
            stream=False,
        )

        answer = (
            ans_or_stream if isinstance(ans_or_stream, str) else "".join(ans_or_stream)
        )
        contexts = [h.get("text") or h.get("content", "") for h in used_hits]
        record_retrieval_hit(bool(contexts))

        duration = time.time() - start
        record_rag_pipeline_latency(duration)
        log_rag_operation(
            success=True,
            duration=duration,
            contexts_count=len(contexts),
            request_id=request_id,
            query_length=len(query),
        )

        reranker_applied = (meta.get("retrieval") or {}).get("reranker")
        meta.update(
            {
                "sources": [h.get("source") for h in used_hits],
                "uids": [h.get("chunk_uid") for h in used_hits],
                "pipeline_duration": round(duration, 3),
                "prompt_version": prompt_version,
                "ab_test_group": ab_test_group,
                "use_rerank": bool(reranker_applied),
            }
        )
        return answer, contexts, meta
    except Exception:
        duration = time.time() - start
        record_rag_pipeline_latency(duration)
        log_rag_operation(
            success=False,
            duration=duration,
            contexts_count=0,
            request_id=request_id,
            query_length=len(query),
        )
        raise
