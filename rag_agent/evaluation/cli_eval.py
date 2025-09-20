# rag_agent/evaluation/cli_eval.py
import argparse
import json
import sys

from rag_agent.evaluation.evaluator import (
    EvaluationConfig,
    dump_results,
    run_evaluation,
)


def main():
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
    )

    per_case, summary = run_evaluation(args.gold, cfg)
    paths = dump_results(per_case, summary, cfg.out_dir)

    print("\n=== Evaluation Summary ===")
    print(json.dumps(summary.__dict__, indent=2))
    print("\nArtifacts:")
    for k, v in paths.items():
        print(f"- {k}: {v}")

    # Failure standard (example): nDCG < 0.6 then fail
    if summary.ndcg_at_k_mean < 0.6:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
