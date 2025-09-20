# scripts/smoke_retrieval.py
import time

from backend.app.core.metrics import record_rag_pipeline_latency
from rag_agent.retrieval.retrieval_pipeline import search_hybrid

if __name__ == "__main__":
    t0 = time.time()
    res = search_hybrid(
        "When are office hours?",
        db_path="./rag_kb.sqlite3",
        k_bm25=25,
        k_vec=25,
        top_k_final=10,
        record_latency=False,  # record in end-to-end
    )
    elapsed = time.time() - t0
    record_rag_pipeline_latency(elapsed)
    print("RESULT N =", len(res))
    for r in res[:3]:
        print(r["chunk_uid"], r["score"], r.get("highlights", [])[:1])
