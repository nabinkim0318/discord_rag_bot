"""
Test-only RAG doubles.

These helpers exist so tests can inject fabricated answers without keeping
mock implementations in application/runtime service modules.
"""

from typing import Any, Dict, List, Optional, Tuple


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
    """Fabricated generate_answer result for explicit test injection."""
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
        "bm25_weight": bm25_weight,
        "vec_weight": vec_weight,
        "mmr_lambda": mmr_lambda,
        "reranker": reranker,
        "stream": stream,
        "filters_fts": filters_fts,
        "filters_weaviate": filters_weaviate,
    }
    return answer, used_hits, metadata


def mock_enhanced_rag_pipeline(
    query: str,
    top_k: int = 5,
    *,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """Fabricated enhanced RAG result for explicit test injection."""
    answer = f"Mock enhanced RAG response for: {query}"
    contexts = [f"Mock context for: {query}"]
    metadata = {
        "user_id": user_id,
        "channel_id": channel_id,
        "request_id": request_id,
        "pipeline": "mock_enhanced_rag",
        "rag_agent_available": False,
        "mock": True,
        "top_k": top_k,
        "sources": ["mock_source"],
        "uids": ["mock_chunk_1"],
    }
    return answer, contexts, metadata
