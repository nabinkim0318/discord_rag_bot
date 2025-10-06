# rag_agent/evaluation/cli_eval.py
import argparse
import json
import os
import random
import sqlite3
import statistics as _stats
import sys
from collections import Counter
from datetime import datetime, timezone

from rag_agent.core.logging import logger
from rag_agent.evaluation.evaluator import (
    EvaluationConfig,
    dump_results,
    run_evaluation,
)


def main():
    # Set random seed for reproducibility
    random.seed(42)

    ap = argparse.ArgumentParser("RAG Evaluator")
    ap.add_argument("--gold", required=True, help="path to gold jsonl")
    ap.add_argument("--sqlite", default="rag_kb.sqlite3")
    ap.add_argument("--k-final", type=int, default=8)
    ap.add_argument("--k-bm25", type=int, default=20)
    ap.add_argument("--k-vec", type=int, default=20)
    ap.add_argument("--bm25-weight", type=float, default=0.4)
    ap.add_argument("--vec-weight", type=float, default=0.6)
    ap.add_argument("--mmr", type=float, default=0.65)
    ap.add_argument("--max-cases", type=int, default=None)
    ap.add_argument("--out-dir", default="rag_agent/evaluation_results")
    # evaluation thresholds
    ap.add_argument("--ndcg-threshold", type=float, default=0.6)
    ap.add_argument("--hit-rate-threshold", type=float, default=0.8)
    ap.add_argument("--latency-threshold", type=float, default=1000.0)
    # guardrails
    ap.add_argument(
        "--fail-fast-uid",
        type=str,
        default="true",
        help="pre-check gold relevant_uids exist in SQLite and exit on missing (true/false)",
    )
    ap.add_argument(
        "--rank-report",
        action="store_true",
        help="print rank distribution report from per-case results",
    )
    # new ranking options
    ap.add_argument(
        "--use-rerank", type=str, default="false", help="enable reranking (true/false)"
    )
    ap.add_argument("--rerank-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    ap.add_argument("--preselect-topn", type=int, default=50)
    ap.add_argument("--per-doc-cap", type=int, default=3)
    ap.add_argument("--rrf-c", type=int, default=15)
    # additional options
    ap.add_argument(
        "--prometheus", action="store_true", help="generate Prometheus metrics file"
    )
    args = ap.parse_args()

    # --- Fail-fast UID existence pre-check (SQLite) ---
    if args.fail_fast_uid.lower() == "true":
        db_path = args.sqlite
        if not os.path.exists(db_path):
            logger.warning(f"SQLite not found at {db_path}; skipping UID precheck")
        else:
            miss = []
            try:
                con = sqlite3.connect(db_path)
                cur = con.cursor()
                with open(args.gold, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if not line.strip():
                            continue
                        try:
                            case = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        for uid in case.get("relevant_uids", []) or []:
                            cur.execute(
                                "SELECT 1 FROM chunks WHERE chunk_uid=? LIMIT 1", (uid,)
                            )
                            if cur.fetchone() is None:
                                miss.append((line_no, uid))
            finally:
                try:
                    con.close()
                except Exception:
                    pass
            if miss:
                logger.error(
                    f"[FAIL] {len(miss)} missing UIDs in gold (showing up to 20):"
                )
                for ln, u in miss[:20]:
                    logger.error(f"  line {ln}: {u}")
                sys.exit(1)
            else:
                logger.info("[OK] all relevant_uids exist in SQLite")

    cfg = EvaluationConfig(
        sqlite_path=args.sqlite,
        k_bm25=args.k_bm25,
        k_vec=args.k_vec,
        k_final=args.k_final,
        bm25_weight=args.bm25_weight,
        vec_weight=args.vec_weight,
        mmr_lambda=args.mmr,
        max_cases=args.max_cases,
        out_dir=args.out_dir,
        ndcg_threshold=args.ndcg_threshold,
        hit_rate_threshold=args.hit_rate_threshold,
        latency_threshold_ms=args.latency_threshold,
        # new ranking options
        use_rerank=args.use_rerank.lower() == "true",
        use_mmr=False,  # Default to False for now
        preselect_topn=args.preselect_topn,
        per_doc_cap=args.per_doc_cap,
        rrf_c=args.rrf_c,
    )

    per_case, summary = run_evaluation(args.gold, cfg)
    paths = dump_results(per_case, summary, cfg.out_dir)

    # --- Rank distribution report ---
    if args.rank_report:
        cases_path = paths.get("cases") or os.path.join(
            cfg.out_dir, "cases_latest.jsonl"
        )
        ranks = []
        try:
            with open(cases_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rel = set(c.get("relevant_uids", []))
                    ranked = c.get("ranked_uids", [])
                    rnk = None
                    for i, uid in enumerate(ranked, 1):
                        if uid in rel:
                            rnk = i
                            break
                    ranks.append(rnk or 999)
            cnt = Counter(ranks)
            top10 = {k: v for k, v in cnt.items() if k <= 10}
            finite = [r for r in ranks if r < 999]
            med = _stats.median(finite) if finite else None
            logger.info(f"Rank histogram (Top-10): {top10}")
            logger.info(f"Median rank (hits only): {med}")
        except FileNotFoundError:
            logger.warning(
                f"rank report requested but cases file not found: {cases_path}"
            )

    # Generate Prometheus metrics file if requested
    if args.prometheus:
        prom_path = os.path.join(cfg.out_dir, "evaluation_metrics.prom")
        with open(prom_path, "w") as fo:
            fo.write("# RAG Evaluation Metrics\n")
            fo.write(f"# Generated at {datetime.now(timezone.utc).isoformat()}\n")
            fo.write(f"rag_eval_total {summary.total}\n")
            fo.write(f"rag_eval_ndcg_at_k {summary.ndcg_at_k_mean}\n")
            fo.write(f"rag_eval_hit_rate {summary.hit_rate}\n")
            fo.write(f"rag_eval_latency_ms {summary.latency_ms_mean}\n")
            fo.write(f"rag_eval_passed {1 if summary.passed else 0}\n")
        paths["prometheus"] = prom_path

    logger.info("\n=== Evaluation Summary ===")
    logger.info(json.dumps(summary.__dict__, indent=2))
    logger.info("\nArtifacts:")
    for k, v in paths.items():
        logger.info(f"- {k}: {v}")

    # Use the new threshold-based pass/fail logic
    if not summary.passed:
        logger.warning(f"\n❌ Evaluation FAILED: {summary.failure_reason}")
        sys.exit(1)
    else:
        logger.info("\n✅ Evaluation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
