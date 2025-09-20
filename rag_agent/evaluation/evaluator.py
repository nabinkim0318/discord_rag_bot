# rag_agent/evaluation/evaluator.py
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rag_agent.evaluation.metrics import (
    ap_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from rag_agent.search.hybrid_search import hybrid_retrieve


@dataclass
class EvaluationConfig:
    sqlite_path: str = "rag_kb.sqlite3"
    k_bm25: int = 20
    k_vec: int = 20
    k_final: int = 8
    bm25_weight: float = 0.4
    vec_weight: float = 0.6
    mmr_lambda: float = 0.65
    max_cases: Optional[int] = None  # When sampling evaluation
    out_dir: str = "rag_agent/evaluation_results"


@dataclass
class CaseResult:
    qid: str
    question: str
    k: int
    retrieved: List[Dict[str, Any]]  # top-k original results (needed fields)
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
    hit_rate: float  # top-k contains relevant


def _apply_filters_to_hybrid_args(filters: Optional[Dict[str, Any]]):
    """
    gold filters to parameters for BM25/Weaviate
    now source=... only one example
    """
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


def run_evaluation(
    gold_path: str, cfg: EvaluationConfig
) -> Tuple[List[CaseResult], EvalSummary]:
    os.makedirs(cfg.out_dir, exist_ok=True)

    # load gold
    cases = []
    with open(gold_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cases.append(json.loads(line))

    if cfg.max_cases:
        random.seed(42)
        cases = random.sample(cases, k=min(cfg.max_cases, len(cases)))

    per_case: List[CaseResult] = []
    ranked_list_all: List[List[str]] = []
    relevant_all: List[Set[str]] = []
    latencies: List[int] = []
    hit_count = 0

    for c in cases:
        qid = c["qid"]
        q = c["question"]
        rel_uids = set(c.get("relevant_uids", []))
        k_final = int(c.get("k", cfg.k_final))
        filters = c.get("filters")

        where_fts, weav_where = _apply_filters_to_hybrid_args(filters)

        t0 = time.perf_counter()
        hits = hybrid_retrieve(
            q,
            sqlite_path=cfg.sqlite_path,
            k_bm25=cfg.k_bm25,
            k_vec=cfg.k_vec,
            k_final=k_final,
            bm25_weight=cfg.bm25_weight,
            vec_weight=cfg.vec_weight,
            mmr_lambda=cfg.mmr_lambda,
            where_fts=where_fts,
            weaviate_where=weav_where,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        ranked_uids = [h["chunk_uid"] for h in hits]
        p = precision_at_k(ranked_uids, rel_uids, k_final)
        r = recall_at_k(ranked_uids, rel_uids, k_final)
        n = ndcg_at_k(ranked_uids, rel_uids, k_final)
        mrr = mrr_at_k(ranked_uids, rel_uids, k_final)
        ap = ap_at_k(ranked_uids, rel_uids, k_final)

        if any(uid in rel_uids for uid in ranked_uids[:k_final]):
            hit_count += 1

        case = CaseResult(
            qid=qid,
            question=q,
            k=k_final,
            retrieved=hits,
            ranked_uids=ranked_uids,
            relevant_uids=list(rel_uids),
            p_at_k=p,
            r_at_k=r,
            ndcg_at_k=n,
            mrr_at_k=mrr,
            ap_at_k=ap,
            latency_ms=latency_ms,
            filters=filters,
        )
        per_case.append(case)
        ranked_list_all.append(ranked_uids)
        relevant_all.append(rel_uids)
        latencies.append(latency_ms)

    # summary
    def mean(xs: List[float]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    p_mean = mean([c.p_at_k for c in per_case])
    r_mean = mean([c.r_at_k for c in per_case])
    ndcg_mean = mean([c.ndcg_at_k for c in per_case])
    mrr_mean = mean([c.mrr_at_k for c in per_case])
    map_mean = mean([c.ap_at_k for c in per_case])
    lat_mean = mean(latencies)
    hit_rate = hit_count / len(per_case) if per_case else 0.0

    summary = EvalSummary(
        total=len(per_case),
        p_at_k_mean=p_mean,
        r_at_k_mean=r_mean,
        ndcg_at_k_mean=ndcg_mean,
        mrr_at_k_mean=mrr_mean,
        map_at_k_mean=map_mean,
        avg_latency_ms=lat_mean,
        hit_rate=hit_rate,
    )
    return per_case, summary


def dump_results(
    per_case: List[CaseResult], summary: EvalSummary, out_dir: str
) -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    per_case_path = os.path.join(out_dir, f"cases_{ts}.jsonl")
    with open(per_case_path, "w", encoding="utf-8") as fo:
        for c in per_case:
            fo.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    summary_path = os.path.join(out_dir, f"summary_{ts}.json")
    with open(summary_path, "w", encoding="utf-8") as fo:
        json.dump(asdict(summary), fo, indent=2)

    # CI/Grafana summary metric file (scrape/parse easily)
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
    }
    with open(metrics_path, "w", encoding="utf-8") as fo:
        json.dump(metrics, fo, indent=2)

    return {"cases": per_case_path, "summary": summary_path, "metrics": metrics_path}
