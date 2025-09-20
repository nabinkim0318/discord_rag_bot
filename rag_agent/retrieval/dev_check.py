# rag_agent/retrieval/dev_check.py
from __future__ import annotations

from pprint import pprint
from typing import Any, Dict

from rag_agent.retrieval.keyword import bm25_search
from rag_agent.retrieval.retrieval_pipeline import search_hybrid
from rag_agent.retrieval.vector import vector_search


def compare_three(db_path: str, query: str) -> Dict[str, Any]:
    bm = bm25_search(db_path, query, k=10)
    ve = vector_search(query, k=10)
    hy = search_hybrid(
        query,
        db_path=db_path,
        k_bm25=25,
        k_vec=25,
        top_k_final=10,
        record_latency=False,
    )

    def brief(xs, key):
        return [(x["chunk_uid"], round(float(x.get(key, 0.0)), 4)) for x in xs[:5]]

    out = {
        "bm25_top5": brief(bm, "score_bm25"),
        "vec_top5": brief(ve, "score_vec"),
        "hybrid_top10": [(x["chunk_uid"], round(float(x["score"]), 4)) for x in hy],
    }
    pprint(out)
    return out


if __name__ == "__main__":
    compare_three("./rag_kb.sqlite3", "When are office hours?")
