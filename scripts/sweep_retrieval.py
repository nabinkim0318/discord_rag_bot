#!/usr/bin/env python3
"""
Retrieval parameter sweep (RRF + MMR) without LLM cost
- Evaluates hybrid search quality using a lightweight, label-driven scoring
- Saves run-level and per-query metrics as CSV
Usage:
  python scripts/sweep_retrieval.py \
    --sqlite ./rag_kb.sqlite3 \
    --dataset evaluation/sample_eval_set.jsonl \
    --out results/sweep_run.csv \
    --kb 40 60 \
    --kv 40 60 \
    --bm25w 0.3 0.4 0.5 \
    --vecw 0.7 0.6 0.5 \
    --mmr 0.55 0.65 0.75 \
    --kfinal 8 10
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

# --- Project imports ---
try:
    # New pipeline wrapper (RRF+MMR under the hood)
    from rag_agent.retrieval.retrieval_pipeline import search_hybrid
except Exception as e:
    raise SystemExit(f"Failed to import retrieval pipeline: {e}")


def load_eval_set(path: str) -> List[Dict[str, Any]]:
    """
    JSONL format per line:
    {
      "query": "When are office hours?",
      "must_have": ["office hours", "time"],     # optional list of keywords
      "gold_snippets": ["Office hours are", ...],# optional list of substrings
      "gold_sources": ["Intern FAQ - AI Bootcamp.pdf"],  # optional list of source names
      "filters": {"doc_type":"schedule","week":2,"audience":"engineer"}  # optional
    }
    """
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def score_single(
    query: str, contexts: List[Dict[str, Any]], case: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute simple, label-light metrics:
    - hit@k (gold_snippets in any context)
    - src@k (any of gold_sources appears)
    - kw@k  (any must_have keyword appears)
    - coverage (fraction of must_have found)
    """
    gold_snips = case.get("gold_snippets") or []
    gold_srcs = [s.lower() for s in (case.get("gold_sources") or [])]
    must_have = case.get("must_have") or []

    texts = [(c.get("content") or c.get("text") or "") for c in contexts]
    sources = [str(c.get("source", "")).lower() for c in contexts]

    hit = 0
    if gold_snips:
        hit = int(
            any(
                any(gs.lower() in (t or "").lower() for gs in gold_snips) for t in texts
            )
        )

    src_hit = 0
    if gold_srcs:
        src_hit = int(any(s in sources for s in gold_srcs))

    kw_hit = 0
    coverage = 0.0
    if must_have:
        kw_hit = int(any(contains_any(t, must_have) for t in texts))
        found = set()
        for k in must_have:
            if any((k.lower() in (t or "").lower()) for t in texts):
                found.add(k.lower())
        coverage = len(found) / max(1, len(must_have))

    return {
        "hit": hit,  # 0/1
        "src_hit": src_hit,  # 0/1
        "kw_hit": kw_hit,  # 0/1
        "coverage": round(coverage, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, help="Path to rag_kb.sqlite3")
    ap.add_argument("--dataset", required=True, help="JSONL eval set")
    ap.add_argument("--out", default="results/sweep_run.csv", help="CSV output path")
    ap.add_argument("--kb", nargs="+", type=int, default=[60], help="k_bm25 candidates")
    ap.add_argument("--kv", nargs="+", type=int, default=[60], help="k_vec candidates")
    ap.add_argument(
        "--bm25w",
        nargs="+",
        type=float,
        default=[0.4],
        help="RRF BM25 weight candidates",
    )
    ap.add_argument(
        "--vecw", nargs="+", type=float, default=[0.6], help="RRF Vec weight candidates"
    )
    ap.add_argument(
        "--mmr", nargs="+", type=float, default=[0.65], help="MMR lambda candidates"
    )
    ap.add_argument(
        "--kfinal", nargs="+", type=int, default=[8], help="final top-k candidates"
    )
    ap.add_argument(
        "--weaviate_where", type=str, default=None, help="JSON for weaviate filter"
    )
    args = ap.parse_args()

    eval_set = load_eval_set(args.dataset)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "kb",
        "kv",
        "bm25w",
        "vecw",
        "mmr",
        "kfinal",
        "n",
        "hit_rate",
        "src_hit_rate",
        "kw_hit_rate",
        "avg_coverage",
        "avg_latency_s",
    ]
    per_query_fields = [
        "kb",
        "kv",
        "bm25w",
        "vecw",
        "mmr",
        "kfinal",
        "idx",
        "query",
        "hit",
        "src_hit",
        "kw_hit",
        "coverage",
        "latency_s",
        "top_sources",
    ]

    per_query_csv = out_path.parent / (out_path.stem + "_per_query.csv")

    with (
        open(out_path, "w", newline="", encoding="utf-8") as fsum,
        open(per_query_csv, "w", newline="", encoding="utf-8") as fdetail,
    ):
        sum_writer = csv.DictWriter(fsum, fieldnames=fieldnames)
        sum_writer.writeheader()
        det_writer = csv.DictWriter(fdetail, fieldnames=per_query_fields)
        det_writer.writeheader()

        where_json = None
        if args.weaviate_where:
            try:
                where_json = json.loads(args.weaviate_where)
            except Exception as e:
                raise SystemExit(f"--weaviate_where JSON parse error: {e}")

        for kb, kv, bw, vw, mmr, kf in product(
            args.kb, args.kv, args.bm25w, args.vecw, args.mmr, args.kfinal
        ):
            n = len(eval_set)
            hits = src_hits = kw_hits = 0
            cov_sum = 0.0
            lat_sum = 0.0

            for i, case in enumerate(eval_set):
                q = case["query"]
                filters_sqlite = case.get("filters")  # doc_type/week/audience

                t0 = time.time()
                try:
                    results = search_hybrid(
                        query=q,
                        db_path=args.sqlite,
                        k_bm25=kb,
                        k_vec=kv,
                        top_k_final=kf,
                        sqlite_filters=filters_sqlite,
                        weaviate_filters=where_json,  # global filter (optional)
                        bm25_weight=bw,
                        vec_weight=vw,
                        mmr_lambda=mmr,
                        record_latency=False,
                    )
                except Exception:
                    # Robustness: skip this query but record as zero-scores
                    results = []
                latency = time.time() - t0
                lat_sum += latency

                # Score
                sc = score_single(q, results, case)
                hits += sc["hit"]
                src_hits += sc["src_hit"]
                kw_hits += sc["kw_hit"]
                cov_sum += sc["coverage"]

                # Per-query log
                top_sources = list({str(r.get("source", "")) for r in (results or [])})[
                    :3
                ]
                det_writer.writerow(
                    {
                        "kb": kb,
                        "kv": kv,
                        "bm25w": bw,
                        "vecw": vw,
                        "mmr": mmr,
                        "kfinal": kf,
                        "idx": i,
                        "query": q,
                        "hit": sc["hit"],
                        "src_hit": sc["src_hit"],
                        "kw_hit": sc["kw_hit"],
                        "coverage": sc["coverage"],
                        "latency_s": round(latency, 4),
                        "top_sources": "|".join(top_sources),
                    }
                )

            # Summary per config
            sum_writer.writerow(
                {
                    "kb": kb,
                    "kv": kv,
                    "bm25w": bw,
                    "vecw": vw,
                    "mmr": mmr,
                    "kfinal": kf,
                    "n": n,
                    "hit_rate": round(hits / max(1, n), 4),
                    "src_hit_rate": round(src_hits / max(1, n), 4),
                    "kw_hit_rate": round(kw_hits / max(1, n), 4),
                    "avg_coverage": round(cov_sum / max(1, n), 4),
                    "avg_latency_s": round(lat_sum / max(1, n), 4),
                }
            )

    print(f"[OK] Wrote summary: {out_path}")
    print(f"[OK] Wrote per-query: {per_query_csv}")


if __name__ == "__main__":
    main()
