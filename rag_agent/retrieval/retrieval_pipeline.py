# rag_agent/retrieval/retrieval_pipeline.py
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.core.metrics import (
    record_failure_metric,
    record_rag_pipeline_latency,
    record_retrieval_hit,
    record_retriever_topk,
)

from rag_agent.retrieval.fuse import mmr_select, rrf_combine
from rag_agent.retrieval.keyword import bm25_search
from rag_agent.retrieval.vector import vector_search

log = logging.getLogger(__name__)


def _sqlite_where_from_filters(filters: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    very simple where builder (extend if needed).
    e.g. {"source": "Training.pdf"} → "source = 'Training.pdf'"
    """
    if not filters:
        return None
    conds = []
    for k, v in filters.items():
        if v is None:
            continue
        if isinstance(v, (int, float)):
            conds.append(f"{k} = {v}")
        else:
            vv = str(v).replace("'", "''")
            conds.append(f"{k} = '{vv}'")
    return " AND ".join(conds) if conds else None


def _llm_ready(items: List[Dict]) -> List[Dict]:
    """
    Convert to LLM-ready format.
    """
    out = []
    for it in items:
        out.append(
            {
                "chunk_uid": it["chunk_uid"],
                "content": it.get("content"),
                "score": float(it.get("score_rrf", 0.0)),
                "doc_id": it.get("doc_id"),
                "source": it.get("source"),
                "page": it.get("page"),
                "highlights": it.get("highlights") or [],
            }
        )
    return out


def search_hybrid(
    query: str,
    *,
    db_path: str,
    k_bm25: int = 25,
    k_vec: int = 25,
    top_k_final: int = 10,
    sqlite_filters: Optional[Dict[str, Any]] = None,
    weaviate_filters: Optional[Dict[str, Any]] = None,
    embed_model: Optional[str] = None,
    mmr_lambda: float = 0.6,
    # weights for RRF combination
    bm25_weight: float = 1.0,
    vec_weight: float = 1.0,
    # metrics/options
    record_latency: bool = True,
    metrics_endpoint: str = "/api/v1/rag/retrieval",
) -> List[Dict]:
    """
    1) BM25 k, Vector k search
    2) RRF combine
    3) MMR diversity correction → top_k_final
    4) LLM-ready format
    """
    t0 = time.time()
    where = _sqlite_where_from_filters(sqlite_filters)

    # ── BM25
    try:
        bm = bm25_search(db_path, query, k=k_bm25, where=where)
    except Exception as e:
        record_failure_metric(metrics_endpoint, "bm25_search_error")
        log.exception("bm25_search failed, %s", e)
        bm = []

    # ── Vector
    try:
        ve = vector_search(
            query, k=k_vec, filters=weaviate_filters, embed_model=embed_model
        )
    except Exception as e:
        record_failure_metric(metrics_endpoint, "vector_search_error")
        log.exception("vector_search failed, %s", e)
        ve = []

    # log: top 3 of each
    def _peek(name, arr, key):
        tops = [(a.get("chunk_uid"), round(float(a.get(key, 0.0)), 4)) for a in arr[:3]]
        log.info("[retrieval] %s top3: %s", name, tops)

    _peek("bm25", bm, "score_bm25")
    _peek("vec", ve, "score_vec")

    # ── RRF + MMR (with weights)
    fused = rrf_combine(
        [bm, ve],
        score_keys=["score_bm25", "score_vec"],
        weights=[bm25_weight, vec_weight],
    )
    mmr = mmr_select(fused, lambda_=mmr_lambda, topn=top_k_final, text_key="content")

    # ── record metrics
    took = time.time() - t0
    try:
        record_retriever_topk(top_k_final)
        record_retrieval_hit(bool(mmr))  # whether at least one context was retrieved
        if record_latency:
            # if there is no separate retrieval-specific histogram, record in
            # pipeline latency (label separated by endpoint)
            record_rag_pipeline_latency(took)
    except Exception as e:
        log.exception("metric failure, %s", e)
        # ignore metric failure as it does not affect functionality
        pass

    log.info(
        "[retrieval] hybrid len(bm,vec,fused,final)=(%d,%d,%d,%d) took=%.3fs",
        len(bm),
        len(ve),
        len(fused),
        len(mmr),
        took,
    )
    return _llm_ready(mmr)
