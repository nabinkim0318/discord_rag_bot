# rag_agent/generation/generation_pipeline.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from rag_agent.generation.context_packer import pack_contexts, render_context_block
from rag_agent.generation.llm_client import llm_generate
from rag_agent.generation.prompting import build_rag_prompt
from rag_agent.retrieval.reranker import maybe_rerank
from rag_agent.search.hybrid_search import hybrid_retrieve

from app.core.config import settings

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def generate_answer(
    query: str,
    *,
    k_bm25: int = 20,
    k_vec: int = 20,
    k_final: int = 8,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
    mmr_lambda: float = 0.65,
    reranker: Optional[str] = None,  # None|'cohere'|'jina'
    prompt_version: str = "v1.1",
    stream: bool = False,
    filters_fts: Optional[str] = None,
    filters_weaviate: Optional[Dict[str, Any]] = None,
) -> Tuple[str | Generator[str, None, None], List[Dict[str, Any]], Dict[str, Any]]:
    """
    return: (answer or stream, used_contexts(hits), metadata)
    """
    # 1) search
    hits = hybrid_retrieve(
        query,
        sqlite_path="rag_kb.sqlite3",
        k_bm25=k_bm25,
        k_vec=k_vec,
        k_final=k_final,
        bm25_weight=bm25_weight,
        vec_weight=vec_weight,
        mmr_lambda=mmr_lambda,
        where_fts=filters_fts,
        weaviate_where=filters_weaviate,
    )

    # 2) (optional) rerank
    hits = maybe_rerank(query, hits, reranker)

    # 3) context packing
    chosen, pack_meta = pack_contexts(
        hits,
        prompt_header_tokens=600,
        max_budget=settings.PROMPT_TOKEN_BUDGET,
        model_hint=settings.OPENAI_MODEL,
    )
    context_block = render_context_block(chosen)

    # 4) prompt generation
    prompt_data = build_rag_prompt(context_block, query, version=prompt_version)
    prompt = prompt_data["prompt"]

    # 5) LLM call
    output = llm_generate(
        prompt,
        system_prompt="You are a helpful assistant. Answer strictly from context.",
        max_tokens=settings.GENERATION_MAX_TOKENS,
        temperature=0.2,
        stream=stream,
    )

    meta = {
        "retrieval": {
            "num_candidates": len(hits),
            "k_final": k_final,
            "reranker": reranker,
            "bm25_weight": bm25_weight,
            "vec_weight": vec_weight,
            "mmr_lambda": mmr_lambda,
        },
        "packing": pack_meta,
        "prompt": {
            "version": prompt_version,
            "length": len(prompt),
        },
        "model": settings.OPENAI_MODEL,
    }

    return output, chosen, meta
