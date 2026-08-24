# rag_agent/evaluation/evaluator.py
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rag_agent.core.logging import logger
from rag_agent.evaluation.gold import load_gold_jsonl
from rag_agent.evaluation.metrics import (
    ap_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from rag_agent.indexing.sqlite_fts import uid_exists as _fts_uid_exists
from rag_agent.retrieval.retrieval_pipeline import search_hybrid


@dataclass
class EvaluationConfig:
    sqlite_path: str = "rag_kb.sqlite3"
    k_bm25: int = 30
    k_vec: int = 30
    k_final: int = 8
    bm25_weight: float = 0.4
    vec_weight: float = 0.6
    mmr_lambda: float = 0.65
    max_cases: Optional[int] = None  # When sampling evaluation
    out_dir: str = "rag_agent/evaluation_results"
    # evaluation thresholds
    ndcg_threshold: float = 0.4
    hit_rate_threshold: float = 0.5
    latency_threshold_ms: float = 1000.0
    enforce_latency: bool = True
    # retrieval options
    use_rerank: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_mmr: bool = False
    preselect_topn: int = 50
    per_doc_cap: int = 3
    rrf_c: int = 15
    # bm25 = sqlite/FTS only; hybrid = sqlite + vector/Weaviate
    retrieval_mode: str = "hybrid"
    enable_vector: bool = True
    require_vector: bool = False


@dataclass
class CaseResult:
    qid: str
    question: str
    k: int
    retrieved: List[Dict[str, Any]]
    ranked_uids: List[str]
    relevant_uids: List[str]
    p_at_k: float
    r_at_k: float
    ndcg_at_k: float
    mrr_at_k: float
    ap_at_k: float
    latency_ms: int
    filters: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@dataclass
class EvalSummary:
    total: int
    p_at_k_mean: float
    r_at_k_mean: float
    ndcg_at_k_mean: float
    mrr_at_k_mean: float
    map_at_k_mean: float
    avg_latency_ms: float
    hit_rate: float
    ndcg_threshold: float = 0.6
    hit_rate_threshold: float = 0.5
    retrieval_mode: str = "hybrid"
    passed: bool = False
    failure_reason: Optional[str] = None


def _apply_filters_to_hybrid_args(filters: Optional[Dict[str, Any]]):
    """gold filters to parameters for BM25/Weaviate; source=... is the example."""
    where_fts = None
    weav_where = None
    if filters and filters.get("source"):
        src = filters["source"].replace("'", "''")
        where_fts = f"source='{src}'"
        weav_where = {
            "path": ["source"],
            "operator": "Equal",
            "valueString": filters["source"],
        }
    return where_fts, weav_where


def _check_uids_exist(cfg: EvaluationConfig, uids: List[str]) -> Dict[str, bool]:
    exist_map: Dict[str, bool] = {}
    if not uids:
        return exist_map
    for uid in uids:
        try:
            exist_map[uid] = _fts_uid_exists(cfg.sqlite_path, uid)
        except Exception:
            exist_map[uid] = False
    missing = [uid for uid, ok in exist_map.items() if not ok]
    if missing and cfg.enable_vector:
        try:
            from rag_agent.indexing.weaviate_index import (
                fetch_by_chunk_uid as weav_fetch,
            )

            got = weav_fetch(missing)
            for uid in missing:
                if uid in got:
                    exist_map[uid] = True
        except Exception:
            pass
    return exist_map


def run_evaluation(
    gold_path: str, cfg: EvaluationConfig
) -> Tuple[List[CaseResult], EvalSummary]:
    os.makedirs(cfg.out_dir, exist_ok=True)

    cases = load_gold_jsonl(gold_path)

    if cfg.max_cases:
        random.seed(42)
        cases = random.sample(cases, k=min(cfg.max_cases, len(cases)))

    per_case: List[CaseResult] = []
    latencies: List[int] = []
    hit_count = 0

    all_rel_uids: List[str] = []
    for case0 in cases:
        all_rel_uids += case0.get("relevant_uids", [])
    unique_rel_uids = list({uid for uid in all_rel_uids if uid})
    exist_map = _check_uids_exist(cfg, unique_rel_uids)
    uid_missing_rate = (
        sum(1 for _, ok in exist_map.items() if not ok) / max(1, len(exist_map))
        if exist_map
        else 0.0
    )
    if exist_map and uid_missing_rate > 0:
        logger.warning(f"[gold] uid_missing_rate={uid_missing_rate:.3f}")

    for case in cases:
        qid = case["qid"]
        question = case["question"]
        rel_uids = set(case.get("relevant_uids", []))
        k_final = max(1, int(case.get("k", cfg.k_final)))
        filters = case.get("filters")

        _fts_where, weav_where = _apply_filters_to_hybrid_args(filters)

        t0 = time.perf_counter()
        hits = search_hybrid(
            question,
            db_path=cfg.sqlite_path,
            k_bm25=cfg.k_bm25,
            k_vec=cfg.k_vec,
            top_k_final=k_final,
            sqlite_filters=filters if filters else None,
            weaviate_filters=weav_where if cfg.enable_vector else None,
            mmr_lambda=cfg.mmr_lambda,
            bm25_weight=cfg.bm25_weight,
            vec_weight=cfg.vec_weight,
            use_rerank=cfg.use_rerank,
            rerank_model=cfg.rerank_model,
            use_mmr=cfg.use_mmr,
            preselect_topn=cfg.preselect_topn,
            per_doc_cap=cfg.per_doc_cap,
            rrf_c=cfg.rrf_c,
            enable_vector=cfg.enable_vector,
            require_vector=cfg.require_vector,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        ranked_uids = [hit["chunk_uid"] for hit in hits]
        precision = precision_at_k(ranked_uids, rel_uids, k_final)
        recall = recall_at_k(ranked_uids, rel_uids, k_final)
        ndcg = ndcg_at_k(ranked_uids, rel_uids, k_final)
        mrr = mrr_at_k(ranked_uids, rel_uids, k_final)
        ap = ap_at_k(ranked_uids, rel_uids, k_final)

        if any(uid in rel_uids for uid in ranked_uids[:k_final]):
            hit_count += 1

        top1 = hits[0] if hits else {}
        note = (
            f"top1_doc={top1.get('doc_id')}/{top1.get('source')} "
            f"gold={{{','.join(sorted(set(u.split('#')[0] for u in rel_uids)))}}}"
        )

        result = CaseResult(
            qid=qid,
            question=question,
            k=k_final,
            retrieved=hits,
            ranked_uids=ranked_uids,
            relevant_uids=list(rel_uids),
            p_at_k=precision,
            r_at_k=recall,
            ndcg_at_k=ndcg,
            mrr_at_k=mrr,
            ap_at_k=ap,
            latency_ms=latency_ms,
            filters=filters,
            notes=note,
        )
        per_case.append(result)
        latencies.append(latency_ms)

    def mean(xs: List[float]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    p_mean = mean([c.p_at_k for c in per_case])
    r_mean = mean([c.r_at_k for c in per_case])
    ndcg_mean = mean([c.ndcg_at_k for c in per_case])
    mrr_mean = mean([c.mrr_at_k for c in per_case])
    map_mean = mean([c.ap_at_k for c in per_case])
    lat_mean = mean(latencies)
    hit_rate = hit_count / len(per_case) if per_case else 0.0

    passed = True
    failure_reasons = []

    if ndcg_mean < cfg.ndcg_threshold:
        passed = False
        failure_reasons.append(f"nDCG {ndcg_mean:.3f} < threshold {cfg.ndcg_threshold}")

    if hit_rate < cfg.hit_rate_threshold:
        passed = False
        failure_reasons.append(
            f"Hit rate {hit_rate:.3f} < threshold {cfg.hit_rate_threshold}"
        )

    if cfg.enforce_latency and lat_mean > cfg.latency_threshold_ms:
        passed = False
        failure_reasons.append(
            f"Latency {lat_mean:.1f}ms > threshold {cfg.latency_threshold_ms}ms"
        )

    if uid_missing_rate > 0:
        passed = False
        failure_reasons.append(f"gold uid_missing_rate={uid_missing_rate:.3f}")

    summary = EvalSummary(
        total=len(per_case),
        p_at_k_mean=p_mean,
        r_at_k_mean=r_mean,
        ndcg_at_k_mean=ndcg_mean,
        mrr_at_k_mean=mrr_mean,
        map_at_k_mean=map_mean,
        avg_latency_ms=lat_mean,
        hit_rate=hit_rate,
        ndcg_threshold=cfg.ndcg_threshold,
        hit_rate_threshold=cfg.hit_rate_threshold,
        retrieval_mode=cfg.retrieval_mode,
        passed=passed,
        failure_reason="; ".join(failure_reasons) if failure_reasons else None,
    )
    return per_case, summary


def dump_results(
    per_case: List[CaseResult], summary: EvalSummary, out_dir: str
) -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")

    per_case_path = os.path.join(out_dir, f"cases_{ts}.jsonl")
    with open(per_case_path, "w", encoding="utf-8") as fo:
        for case in per_case:
            fo.write(json.dumps(asdict(case), ensure_ascii=False) + "\n")

    summary_path = os.path.join(out_dir, f"summary_{ts}.json")
    with open(summary_path, "w", encoding="utf-8") as fo:
        json.dump(asdict(summary), fo, indent=2)

    metrics_path = os.path.join(out_dir, "evaluation_metrics.json")
    metrics = {
        "rag_eval_total": summary.total,
        "rag_eval_p_at_k": summary.p_at_k_mean,
        "rag_eval_r_at_k": summary.r_at_k_mean,
        "rag_eval_ndcg_at_k": summary.ndcg_at_k_mean,
        "rag_eval_mrr_at_k": summary.mrr_at_k_mean,
        "rag_eval_map_at_k": summary.map_at_k_mean,
        "rag_eval_hit_rate": summary.hit_rate,
        "rag_eval_avg_latency_ms": summary.avg_latency_ms,
        "rag_eval_ndcg_threshold": summary.ndcg_threshold,
        "rag_eval_hit_rate_threshold": summary.hit_rate_threshold,
        "rag_eval_retrieval_mode": summary.retrieval_mode,
        "rag_eval_passed": summary.passed,
        "rag_eval_failure_reason": summary.failure_reason,
        "rag_eval_status": "PASS" if summary.passed else "FAIL",
    }
    with open(metrics_path, "w", encoding="utf-8") as fo:
        json.dump(metrics, fo, indent=2)

    return {"cases": per_case_path, "summary": summary_path, "metrics": metrics_path}
