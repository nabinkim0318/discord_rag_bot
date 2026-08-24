# rag_agent/evaluation/cli_eval.py
"""Retrieval evaluator CLI. Ranks chunk UIDs; does not score generated answers."""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics as stats
import sys
from collections import Counter
from datetime import datetime, timezone

from rag_agent.core.logging import logger
from rag_agent.evaluation.evaluator import (
    EvaluationConfig,
    dump_results,
    run_evaluation,
)
from rag_agent.evaluation.gold import validate_gold_against_sqlite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "RAG retrieval evaluator",
        description=(
            "Evaluate ranked chunk UIDs against gold relevant_uids. "
            "This is retrieval evaluation, not generation/answer quality."
        ),
    )
    parser.add_argument("--gold", required=True, help="path to gold jsonl")
    parser.add_argument("--sqlite", default="rag_kb.sqlite3")
    parser.add_argument(
        "--mode",
        choices=("bm25", "hybrid"),
        default="hybrid",
        help="bm25: sqlite/FTS only. hybrid: sqlite + Weaviate/vector.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="alias for --mode bm25; never call Weaviate or embeddings",
    )
    parser.add_argument("--k-final", type=int, default=8)
    parser.add_argument("--k-bm25", type=int, default=20)
    parser.add_argument("--k-vec", type=int, default=20)
    parser.add_argument("--bm25-weight", type=float, default=0.4)
    parser.add_argument("--vec-weight", type=float, default=0.6)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--out-dir", default="rag_agent/evaluation_results")
    parser.add_argument("--ndcg-threshold", type=float, default=0.6)
    parser.add_argument("--hit-rate-threshold", type=float, default=0.8)
    parser.add_argument("--latency-threshold", type=float, default=1000.0)
    parser.add_argument(
        "--no-latency-gate",
        action="store_true",
        help="record latency but do not fail the gate on it",
    )
    parser.add_argument(
        "--fail-fast-uid",
        type=str,
        default="true",
        help="require sqlite and gold relevant_uids to exist (true/false)",
    )
    parser.add_argument(
        "--rank-report",
        action="store_true",
        help="print rank distribution report from per-case results",
    )
    parser.add_argument(
        "--use-rerank",
        type=str,
        default="false",
        help="enable cross-encoder reranking (true/false)",
    )
    parser.add_argument(
        "--rerank-model",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        help="cross-encoder model name used when rerank is enabled",
    )
    parser.add_argument("--preselect-topn", type=int, default=50)
    parser.add_argument("--per-doc-cap", type=int, default=3)
    parser.add_argument("--rrf-c", type=int, default=15)
    parser.add_argument(
        "--prometheus", action="store_true", help="generate Prometheus metrics file"
    )
    return parser


def config_from_args(args: argparse.Namespace) -> EvaluationConfig:
    mode = "bm25" if args.offline else args.mode
    enable_vector = mode == "hybrid"
    return EvaluationConfig(
        sqlite_path=args.sqlite,
        k_bm25=args.k_bm25,
        k_vec=args.k_vec,
        k_final=args.k_final,
        bm25_weight=args.bm25_weight,
        vec_weight=args.vec_weight,
        max_cases=args.max_cases,
        out_dir=args.out_dir,
        ndcg_threshold=args.ndcg_threshold,
        hit_rate_threshold=args.hit_rate_threshold,
        latency_threshold_ms=args.latency_threshold,
        enforce_latency=not args.no_latency_gate,
        use_rerank=args.use_rerank.lower() == "true",
        rerank_model=args.rerank_model,
        use_mmr=False,
        preselect_topn=args.preselect_topn,
        per_doc_cap=args.per_doc_cap,
        rrf_c=args.rrf_c,
        retrieval_mode=mode,
        enable_vector=enable_vector,
        require_vector=enable_vector,
    )


def _fail_fast_uids(gold_path: str, sqlite_path: str) -> None:
    if not os.path.exists(sqlite_path):
        logger.error(
            f"[FAIL] sqlite index not found at {sqlite_path}. "
            "Build it first (make eval-rag-demo-index)."
        )
        sys.exit(1)
    try:
        _records, missing = validate_gold_against_sqlite(gold_path, sqlite_path)
    except ValueError as exc:
        logger.error(f"[FAIL] gold validation: {exc}")
        sys.exit(1)
    if missing:
        logger.error(f"[FAIL] {len(missing)} gold UIDs missing from sqlite:")
        for uid in missing[:20]:
            logger.error(f"  {uid}")
        sys.exit(1)
    logger.info("[OK] gold JSONL is valid and all relevant_uids exist in sqlite")


def main(argv: list[str] | None = None) -> int:
    random.seed(42)
    args = build_parser().parse_args(argv)
    cfg = config_from_args(args)

    if args.fail_fast_uid.lower() == "true":
        _fail_fast_uids(args.gold, args.sqlite)

    try:
        per_case, summary = run_evaluation(args.gold, cfg)
    except ValueError as exc:
        logger.error(f"[FAIL] evaluation aborted: {exc}")
        return 1
    except Exception as exc:
        if cfg.retrieval_mode == "hybrid" and cfg.require_vector:
            logger.error(
                "Hybrid retrieval evaluation could not run. "
                "Weaviate and an embedding provider must be configured. "
                f"Original error: {exc}"
            )
            return 2
        raise

    paths = dump_results(per_case, summary, cfg.out_dir)

    if args.rank_report:
        cases_path = paths.get("cases") or os.path.join(
            cfg.out_dir, "cases_latest.jsonl"
        )
        ranks = []
        try:
            with open(cases_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        case = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rel = set(case.get("relevant_uids", []))
                    ranked = case.get("ranked_uids", [])
                    rank = next(
                        (i for i, uid in enumerate(ranked, 1) if uid in rel), 999
                    )
                    ranks.append(rank)
            counts = Counter(ranks)
            top10 = {k: v for k, v in counts.items() if k <= 10}
            finite = [r for r in ranks if r < 999]
            median = stats.median(finite) if finite else None
            logger.info(f"Rank histogram (Top-10): {top10}")
            logger.info(f"Median rank (hits only): {median}")
        except FileNotFoundError:
            logger.warning(
                f"rank report requested but cases file not found: {cases_path}"
            )

    if args.prometheus:
        prom_path = os.path.join(cfg.out_dir, "evaluation_metrics.prom")
        with open(prom_path, "w") as fo:
            fo.write("# RAG retrieval evaluation metrics\n")
            fo.write(f"# Generated at {datetime.now(timezone.utc).isoformat()}\n")
            fo.write(f"rag_eval_total {summary.total}\n")
            fo.write(f"rag_eval_ndcg_at_k {summary.ndcg_at_k_mean}\n")
            fo.write(f"rag_eval_hit_rate {summary.hit_rate}\n")
            fo.write(f"rag_eval_latency_ms {summary.avg_latency_ms}\n")
            fo.write(f"rag_eval_passed {1 if summary.passed else 0}\n")
        paths["prometheus"] = prom_path

    logger.info("\n=== Retrieval Evaluation Summary ===")
    logger.info(json.dumps(summary.__dict__, indent=2))
    logger.info("\nArtifacts:")
    for key, value in paths.items():
        logger.info(f"- {key}: {value}")

    if not summary.passed:
        logger.warning(f"\nEvaluation FAILED: {summary.failure_reason}")
        return 1
    logger.info("\nEvaluation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
