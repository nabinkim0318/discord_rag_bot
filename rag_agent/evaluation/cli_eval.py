# rag_agent/evaluation/cli_eval.py
import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone

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
    # additional options
    ap.add_argument(
        "--prometheus", action="store_true", help="generate Prometheus metrics file"
    )
    args = ap.parse_args()

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
    )

    per_case, summary = run_evaluation(args.gold, cfg)
    paths = dump_results(per_case, summary, cfg.out_dir)

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

    print("\n=== Evaluation Summary ===")
    print(json.dumps(summary.__dict__, indent=2))
    print("\nArtifacts:")
    for k, v in paths.items():
        print(f"- {k}: {v}")

    # Use the new threshold-based pass/fail logic
    if not summary.passed:
        print(f"\n❌ Evaluation FAILED: {summary.failure_reason}")
        sys.exit(1)
    else:
        print("\n✅ Evaluation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
