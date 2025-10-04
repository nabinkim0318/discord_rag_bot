# scripts/smoke_retrieval.py
import time

from rag_agent.core.logging import logger
from rag_agent.retrieval.retrieval_pipeline import search_hybrid

from backend.app.core.metrics import record_rag_pipeline_latency

if __name__ == "__main__":
    t0 = time.time()
    res = search_hybrid(
        "When are office hours?",
        db_path="./rag_kb.sqlite3",
        k_bm25=30,
        k_vec=30,
        top_k_final=8,
        record_latency=False,  # record in end-to-end
    )
    elapsed = time.time() - t0
    record_rag_pipeline_latency(elapsed)
    logger.info(f"RESULT N = {len(res)}")
    for r in res[:3]:
        logger.info(f"{r['chunk_uid']} {r['score']} {r.get('highlights', [])[:1]}")
