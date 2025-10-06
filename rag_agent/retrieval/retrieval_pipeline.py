# rag_agent/retrieval/retrieval_pipeline.py
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from rag_agent.retrieval.fuse import rrf_combine, score_fuse
from rag_agent.retrieval.keyword import bm25_search
from rag_agent.retrieval.rerank import rerank_cross_encoder
from rag_agent.retrieval.vector import vector_search

# Defensive import - prevent crashes when running without backend
try:
    from app.core.metrics import (
        record_failure_metric,
        record_rag_pipeline_latency,
        record_retrieval_hit,
        record_retriever_topk,
    )
except ImportError:
    # Replace with dummy functions when running without backend
    def record_failure_metric(*args, **kwargs):
        pass

    def record_rag_pipeline_latency(*args, **kwargs):
        pass

    def record_retrieval_hit(*args, **kwargs):
        pass

    def record_retriever_topk(*args, **kwargs):
        pass


log = logging.getLogger(__name__)


def _sqlite_where_from_filters(filters: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    very simple where builder (extend if needed).
    e.g. {"source": "Training.pdf"} -> "source = 'Training.pdf'"
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
        # score priority: score_final > score_ce > score_fused > score_rrf
        score_val = (
            float(it.get("score_final"))
            if it.get("score_final") is not None
            else float(it.get("score_ce"))
            if it.get("score_ce") is not None
            else float(it.get("score_fused"))
            if it.get("score_fused") is not None
            else float(it.get("score_rrf", 0.0))
        )
        out.append(
            {
                "chunk_uid": it["chunk_uid"],
                "content": it.get("content"),
                "score": score_val,
                "doc_id": it.get("doc_id"),
                "source": it.get("source"),
                "page": it.get("page"),
                "highlights": it.get("highlights") or [],
            }
        )
    return out


def _apply_doc_prior(items: List[Dict], intent: Optional[str] = None) -> List[Dict]:
    """
    Apply simple document priors to RRF scores based on heuristic intent.
    - Adds small bonuses to 'score_rrf' using source/doc_id hints.
    """
    if not items:
        return items
    it_lower = (intent or "").lower()
    pri_faq = (
        0.10
        if it_lower
        in {"schedule", "communication", "visa", "requirement", "certification", "faq"}
        else 0.0
    )
    pri_training = (
        0.10
        if it_lower in {"resources", "concept", "tasks", "roles", "training"}
        else 0.0
    )
    pri_journey = 0.05
    out: List[Dict] = []
    for it in items:
        src = (it.get("source") or "").lower()
        bonus = 0.0
        if "faq" in src:
            bonus = pri_faq
        elif "training" in src:
            bonus = pri_training
        elif "journey" in src:
            bonus = pri_journey
        it2 = dict(it)
        it2["score_rrf"] = float(it.get("score_rrf", 0.0)) + float(bonus)
        out.append(it2)
    out.sort(key=lambda x: -float(x.get("score_rrf", 0.0)))
    return out


def _optional_rerank(items: List[Dict], topn: int = 50) -> List[Dict]:
    """
    Placeholder for a reranker stage. Currently pass-through.
    Select topn for potential external rerankers.
    """
    if not items:
        return items
    return items[:topn]


def _apply_feature_boost_layer(
    query: str,
    items: List[Dict],
    vec_seed: Optional[Dict],
    lexical_weight: float = 0.15,
    title_weight: float = 0.08,
    position_weight: float = 0.06,
    neighbor_weight: float = 0.05,
) -> List[Dict]:
    """
    Apply feature boost layer for tie-breaking.

    Final score = 1.00 * score_ce + lexical_weight * lexical_overlap +
                  title_weight * title_hit + position_weight * position_prior +
                  neighbor_weight * neighbor_bonus
    """
    if not items or not query:
        return items

    import re

    # Tokenize query (simple whitespace + punctuation split)
    query_tokens = set(re.findall(r"\w+", query.lower()))

    # Get vector seed chunk_uid for neighbor detection
    vec_seed_uid = vec_seed.get("chunk_uid") if vec_seed else None

    boosted_items = []

    for item in items:
        # Base CE score
        score_ce = float(item.get("score_ce", 0.0))

        # 1. Lexical overlap
        content = item.get("content", "")
        content_tokens = set(re.findall(r"\w+", content.lower()))
        lexical_overlap = len(query_tokens & content_tokens) / max(len(query_tokens), 1)

        # 2. Title hit (first 120 chars or metadata)
        title_text = content[:120].lower()
        title_hit = 1.0 if any(token in title_text for token in query_tokens) else 0.0

        # 3. Position prior (earlier chunks get higher priority)
        chunk_id = item.get("chunk_id", 0)
        position_prior = max(0.0, 0.6 - 0.02 * chunk_id)

        # 4. Neighbor bonus (chunks adjacent to vector seed)
        neighbor_bonus = 0.0
        if vec_seed_uid:
            item_uid = item.get("chunk_uid", "")
            if vec_seed_uid and item_uid:
                # Simple neighbor detection: check if chunk_ids are adjacent
                try:
                    vec_chunk_id = int(vec_seed_uid.split("#")[-1])
                    item_chunk_id = int(item_uid.split("#")[-1])
                    if abs(vec_chunk_id - item_chunk_id) <= 1:
                        neighbor_bonus = 0.05
                except (ValueError, IndexError):
                    pass

        # Calculate final score
        score_final = (
            1.00 * score_ce
            + lexical_weight * lexical_overlap
            + title_weight * title_hit
            + position_weight * position_prior
            + neighbor_weight * neighbor_bonus
        )

        # Create boosted item
        boosted_item = item.copy()
        boosted_item["score_final"] = score_final
        boosted_item["score_ce"] = score_ce
        boosted_item["lexical_overlap"] = lexical_overlap
        boosted_item["title_hit"] = title_hit
        boosted_item["position_prior"] = position_prior
        boosted_item["neighbor_bonus"] = neighbor_bonus

        boosted_items.append(boosted_item)

    # Sort by final score (descending), with tie-breaking
    def sort_key(item):
        return (
            -item.get("score_final", 0.0),  # Primary: final score
            -item.get("lexical_overlap", 0.0),  # Secondary: lexical overlap
            -item.get(
                "position_prior", 0.0
            ),  # Tertiary: position prior (lower chunk_id)
            -item.get("score_fused", 0.0),  # Quaternary: fused score
            -item.get("score_rrf", 0.0),  # Quinary: RRF score
        )

    boosted_items.sort(key=sort_key)

    return boosted_items


def search_hybrid(
    query: str,
    *,
    db_path: str,
    k_bm25: int = 30,
    k_vec: int = 30,
    top_k_final: int = 8,
    sqlite_filters: Optional[Dict[str, Any]] = None,
    weaviate_filters: Optional[Dict[str, Any]] = None,
    embed_model: Optional[str] = None,
    # ranking controls
    rrf_c: int = 15,
    use_mmr: bool = False,
    mmr_lambda: float = 0.65,
    preselect_topn: int = 50,
    per_doc_cap: int = 3,
    use_rerank: bool = True,
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    # weights for RRF combination
    bm25_weight: float = 0.2,
    vec_weight: float = 0.8,
    # metrics/options
    record_latency: bool = True,
    metrics_endpoint: str = "/api/v1/rag/retrieval",
) -> List[Dict]:
    """
    1) BM25 k, Vector k search
    2) RRF combine
    3) MMR diversity correction -> top_k_final
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

    # ── Fusion: score-based normalize+sum (primary), with RRF fallback if needed
    try:
        fused = score_fuse(bm, ve, w_bm25=bm25_weight, w_vec=vec_weight)
    except Exception:
        fused = rrf_combine(
            [bm, ve],
            score_keys=["score_bm25", "score_vec"],
            weights=[bm25_weight, vec_weight],
            c=rrf_c,
        )
    # ── 넉넉한 풀 구성 (Protected-Top seeds 포함) + per-doc cap
    present_uids = set()
    pool: List[Dict] = []

    def _add_seed(item: Optional[Dict]):
        if not item:
            return
        uid = item.get("chunk_uid")
        if not uid or uid in present_uids:
            return
        pool.append(item)
        present_uids.add(uid)

    # seeds: ensure bm25 top1 and vector top1
    bm_seed = bm[0] if bm else None
    ve_seed = ve[0] if ve else None
    _add_seed(bm_seed)
    _add_seed(ve_seed)

    # per-doc cap (max per_doc_cap per doc) - include seeds into cap
    max_per_doc = per_doc_cap
    per_doc: Dict[str, int] = {}

    def _doc_id(it: Dict) -> str:
        return it.get("doc_id") or ""

    for s in [bm_seed, ve_seed]:
        if not s:
            continue
        did = _doc_id(s)
        per_doc[did] = per_doc.get(did, 0) + 1
    for it in fused:
        if it.get("chunk_uid") in present_uids:
            continue
        did = it.get("doc_id") or ""
        cnt = per_doc.get(did, 0)
        if cnt >= max_per_doc:
            continue
        per_doc[did] = cnt + 1
        pool.append(it)
        present_uids.add(it.get("chunk_uid"))
        if len(pool) >= max(preselect_topn, top_k_final):
            break
    # Protected-Top: seeds are guaranteed in pool, not in final (except CE-top1)
    # This allows fair competition in final ranking
    final: List[Dict] = []

    # Note: Seeds (bm_seed, ve_seed) are already in pool via _add_seed()
    # No need to force them into final - let CE reranking decide

    # 안전 Fallback 게이트: 상위 두 fused 점수 차가 매우 작고 vec top1이 매우 상위일 때만 top1 교체
    try:
        if len(fused) >= 2 and ve_seed:
            top_diff = float(fused[0].get("score_fused", 0.0)) - float(
                fused[1].get("score_fused", 0.0)
            )
            ve_uids = [x.get("chunk_uid") for x in ve]
            if ve_uids:
                rank_vec = {u: i + 1 for i, u in enumerate(ve_uids)}
                ve_rank = rank_vec.get(ve_seed.get("chunk_uid"))
                top_k_vec = max(1, int(0.05 * len(ve_uids)))
                if ve_rank is not None and top_diff < 0.02 and ve_rank <= top_k_vec:
                    if final and final[0].get("chunk_uid") != ve_seed.get("chunk_uid"):
                        final[0] = ve_seed
    except Exception:
        pass

    # ── (신규) Cross-Encoder rerank (optional)
    try:
        if use_rerank and pool:
            reranked = rerank_cross_encoder(
                query, pool, model_name=rerank_model, text_key="content"
            )
            final = reranked[:top_k_final]
        else:
            # No reranking, use pool directly
            final = pool[:top_k_final]
    except Exception:
        final = pool[:top_k_final]

    # ── (신규) Feature Boost Layer for tie-breaking
    if final and use_rerank:
        try:
            final = _apply_feature_boost_layer(
                query,
                final,
                ve_seed,
                lexical_weight=0.20,  # Moderate boost
                title_weight=0.10,  # Moderate boost
                position_weight=0.08,  # Moderate boost
                neighbor_weight=0.05,  # Small boost
            )

            # Protected-Top: Ensure CE-top1 is included (highest CE score)
            if final:
                ce_top1 = max(final, key=lambda x: float(x.get("score_ce", 0.0)))
                if ce_top1 not in final[:1]:  # If not already at position 1
                    final = [ce_top1] + [item for item in final if item != ce_top1]
                    final = final[:top_k_final]  # Trim to desired length

        except Exception as e:
            log.warning(f"Feature boost layer failed: {e}")
            # Continue with original final list

    # ── record metrics
    took = time.time() - t0
    try:
        record_retriever_topk(top_k_final)
        record_retrieval_hit(bool(final))  # whether at least one context was retrieved
        if record_latency:
            # if there is no separate retrieval-specific histogram, record in
            # pipeline latency (label separated by endpoint)
            record_rag_pipeline_latency(took)
    except Exception as e:
        log.exception("metric failure, %s", e)
        # ignore metric failure as it does not affect functionality
        pass

    # Log feature boost details if applied
    boost_info = ""
    if final and use_rerank and any("score_final" in item for item in final):
        boost_info = " [BOOSTED]"

    log.info(
        "[retrieval] hybrid len(bm,vec,fused,final)=(%d,%d,%d,%d) took=%.3fs%s",
        len(bm),
        len(ve),
        len(fused),
        len(final),
        took,
        boost_info,
    )
    return _llm_ready(final)
