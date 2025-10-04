# rag_agent/search/hybrid_search.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from rag_agent.indexing.sqlite_fts import bm25_search
from rag_agent.search.mmr import mmr_rerank

# ── .env: Repo root only once (match other files)
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


try:
    from rag_agent.indexing.embeddings import embed_texts
except ImportError:
    # fallback for standalone execution
    def embed_texts(texts):
        # dummy implementation - should be replaced with actual embedding
        return [[0.0] * 384 for _ in texts]


# Weaviate v3 client used
try:
    import weaviate
except Exception:
    weaviate = None

# Reuse backend settings (WEAVIATE_URL, WEAVIATE_API_KEY)
try:
    from app.core.config import settings
except Exception:

    class _S:  # For standalone execution
        WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

    settings = _S()

CLASS_NAME = "KBChunk"  # Match the class name created in C-step


# ---------- Utils ----------
# _min_max_norm function removed - using original scores for consistency with RRF


def _weaviate_client():
    if weaviate is None:
        raise RuntimeError("weaviate is not installed")
    cfg = {"url": settings.WEAVIATE_URL}
    if getattr(settings, "WEAVIATE_API_KEY", None):
        cfg["auth_client_secret"] = weaviate.AuthApiKey(
            api_key=settings.WEAVIATE_API_KEY
        )
    return weaviate.Client(**cfg)


# ---------- Vector Search ----------
def vector_search_weaviate_by_query_vec(
    query_vec: List[float],
    *,
    top_k: int = 20,
    where_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Search KBChunk by nearVector (vectorizer: none)
    Return: [{chunk_uid, content, source, doc_id, chunk_id,
    page, metadata, score_vec}, ...]
    """
    c = _weaviate_client()
    try:
        qb = (
            c.query.get(
                CLASS_NAME,
                [
                    "content",
                    "source",
                    "doc_id",
                    "chunk_id",
                    "page",
                    "chunk_uid",
                    "metadata_json",
                ],
            )
            .with_near_vector({"vector": query_vec})
            .with_limit(top_k)
            .with_additional(
                ["id", "distance"]
            )  # cosine distance(0=identical, 2=opposite) or dot based on settings
        )
        if where_filter:
            qb = qb.with_where(where_filter)

        res = qb.do()
        items = res.get("data", {}).get("Get", {}).get(CLASS_NAME, []) or []
        out = []
        for it in items:
            md = {}
            try:
                md = json.loads(it.get("metadata_json") or "{}")
            except Exception:
                md = {}

            # distance → similarity (standardized with vector.py)
            add = it["_additional"] or {}
            # Use certainty if available (0~1), otherwise 1 - distance
            if "certainty" in add and add["certainty"] is not None:
                sim = float(add["certainty"])
            else:
                dist = float(add.get("distance", 1.0))
                sim = max(0.0, 1.0 - dist)

            out.append(
                {
                    "chunk_uid": it.get("chunk_uid"),
                    "content": it.get("content"),
                    "source": it.get("source"),
                    "doc_id": it.get("doc_id"),
                    "chunk_id": it.get("chunk_id"),
                    "page": it.get("page"),
                    "metadata": md,
                    "score_vec": sim,  # Standardized key name
                }
            )
        return out
    finally:
        c.close()


# ---------- Adapter for new retrieval pipeline ----------
def hybrid_retrieve_v2(
    query: str,
    *,
    sqlite_path: str,
    k_bm25: int = 30,
    k_vec: int = 30,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    where_fts: Optional[str] = None,
    weaviate_where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Adapter: use new retrieval pipeline but maintain existing signature
    Weight parameters are used for fine-tuning in RRF+MMR structure
    Weight parameters are used for fine-tuning in RRF+MMR structure
    """
    from rag_agent.retrieval.retrieval_pipeline import search_hybrid

    # where_fts to sqlite_filters
    sqlite_filters = None
    if where_fts:
        # simple parsing: "source='file.pdf'" -> {"source": "file.pdf"}
        if "=" in where_fts:
            parts = where_fts.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                sqlite_filters = {key: value}

    # New pipeline call (with weights)
    results = search_hybrid(
        query,
        db_path=sqlite_path,
        k_bm25=k_bm25,
        k_vec=k_vec,
        top_k_final=k_final,
        sqlite_filters=sqlite_filters,
        weaviate_filters=weaviate_where,
        mmr_lambda=mmr_lambda,
        bm25_weight=bm25_weight,
        vec_weight=vec_weight,
        record_latency=False,  # disable metrics for evaluation
    )

    # Convert to legacy format (score -> combined, add bm25/score_vec)
    converted = []
    for item in results:
        converted_item = {
            "chunk_uid": item["chunk_uid"],
            "content": item["content"],
            "source": item.get("source"),
            "doc_id": item.get("doc_id"),
            "chunk_id": item.get("chunk_id"),
            "text": item.get("content"),
            "page": item.get("page"),
            "combined": item["score"],  # RRF+MMR final score
            "bm25": 0.0,  # RRF is hard to separate individual scores
            "score_vec": 0.0,  # RRF is hard to separate individual scores
        }
        converted.append(converted_item)

    return converted


# ---------- Hybrid Search (BM25 + Vector) ----------
def hybrid_retrieve(
    query: str,
    *,
    sqlite_path: str,
    k_bm25: int = 20,
    k_vec: int = 20,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    where_fts: Optional[str] = None,  # e.g. "source='Intern FAQ - AI Bootcamp.pdf'"
    weaviate_where: Optional[
        Dict[str, Any]
    ] = None,  # Same filter applied to vector side
) -> List[Dict[str, Any]]:
    """
    Hybrid search - use new RRF+MMR pipeline
    but maintain existing signature internally

    Args:
        bm25_weight, vec_weight: RRF+MMR structure only for fine-tuning
        (actual weights are automatically calculated in RRF)

    Return: [{chunk_uid, content, source, doc_id,
    chunk_id, page, combined, bm25, score_vec}, ...]
    """
    # use new pipeline (call adapter function)
    return hybrid_retrieve_v2(
        query,
        sqlite_path=sqlite_path,
        k_bm25=k_bm25,
        k_vec=k_vec,
        k_final=k_final,
        bm25_weight=bm25_weight,
        vec_weight=vec_weight,
        mmr_lambda=mmr_lambda,
        where_fts=where_fts,
        weaviate_where=weaviate_where,
    )


def hybrid_retrieve_legacy(
    query: str,
    *,
    sqlite_path: str,
    k_bm25: int = 20,
    k_vec: int = 20,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    where_fts: Optional[str] = None,  # e.g. "source='Intern FAQ - AI Bootcamp.pdf'"
    weaviate_where: Optional[
        Dict[str, Any]
    ] = None,  # Same filter applied to vector side
) -> List[Dict[str, Any]]:
    """
    Legacy hybrid search (existing implementation)
    1) FTS5 BM25 top-k
    2) Embedding -> Weaviate nearVector top-k
    3) Normalize + weighted sum for base score
    4) MMR for final k_final reranking
    Return: [{chunk_uid, content, source, doc_id,
    chunk_id, page, score, bm25, score_vec}, ...]
    """
    # --- 1) BM25 ---
    bm25_hits = bm25_search(sqlite_path, query, k=k_bm25, where=where_fts)
    # Use original BM25 scores (smaller is better) - consistent with RRF approach
    # RRF is rank-based so score direction doesn't matter much

    bm25_map = {}  # chunk_uid → (payload, score)
    for h in bm25_hits:
        bm25_map[h["chunk_uid"]] = (
            {
                "chunk_uid": h["chunk_uid"],
                "content": h["text"],
                "source": h.get("source"),
                "doc_id": h.get("doc_id"),
                "chunk_id": h.get("chunk_id"),
                "page": h.get("page"),
            },
            float(h.get("bm25", 0.0)),  # Use original BM25 score
        )

    # --- 2) Vector top-k ---
    [query_vec] = embed_texts([query])  # Query embedding
    vec_hits = vector_search_weaviate_by_query_vec(
        query_vec, top_k=k_vec, where_filter=weaviate_where
    )

    # Use original score_vec values (0..1) - consistent with RRF approach
    vec_map = {h["chunk_uid"]: (h, h["score_vec"]) for h in vec_hits}

    # --- 3) Merge candidates + base score (weighted sum) ---
    # Merge by same chunk_uid
    all_uids = set(bm25_map.keys()) | set(vec_map.keys())
    merged = []
    for uid in all_uids:
        b_payload, b_s = bm25_map.get(uid, ({}, 0.0))
        v_payload, v_s = vec_map.get(uid, ({}, 0.0))

        # content/source etc. is used if filled from either side
        payload = (
            b_payload
            if b_payload
            else {
                "chunk_uid": v_payload.get("chunk_uid"),
                "content": v_payload.get("content"),
                "source": v_payload.get("source"),
                "doc_id": v_payload.get("doc_id"),
                "chunk_id": v_payload.get("chunk_id"),
                "page": v_payload.get("page"),
            }
        )

        combined = bm25_weight * b_s + vec_weight * v_s
        payload.update(
            {
                "bm25": b_s,
                "score_vec": v_s,  # Standardized key name
                "combined": combined,
            }
        )
        merged.append(payload)

    if not merged:
        return []

    # --- 4) MMR reranking: diversity ---
    # MMR needs similarity between documents → need candidate text embedding
    cand_texts = [m["content"] for m in merged]
    cand_vecs = embed_texts(cand_texts)

    # Choose final k_final candidates with MMR
    # (similarity is query_vec vs cand_vec)
    reranked = mmr_rerank(
        query_vec=query_vec,
        cand_vecs=cand_vecs,
        cand_payloads=merged,
        k=k_final,
        lambda_=mmr_lambda,
    )

    # Sort by score in descending order (for convenience)
    reranked.sort(key=lambda x: x.get("combined", 0.0), reverse=True)
    return reranked
