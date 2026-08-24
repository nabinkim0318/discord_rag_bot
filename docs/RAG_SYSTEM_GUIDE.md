# RAG pipeline (live path)

This describes what **`generate_answer`** actually runs for HTTP RAG. Configuration knobs and unused modules are called out separately.

Package: [`rag_agent/`](../rag_agent/). The API does not spawn a second RAG container.

## Call chain

```text
POST /api/query/ | /api/v1/rag/ | /api/v1/enhanced-rag/
  → backend service
  → rag_agent.generation.generation_pipeline.generate_answer
  → hybrid_retrieve → hybrid_retrieve_v2 → search_hybrid
  → optional Cohere/Jina maybe_rerank
  → pack_contexts → build_rag_prompt → llm_generate
```

`/api/v1/enhanced-rag/` uses the same `generate_answer` function. It does **not** run a separate query-planner / multi-intent router. Differences: metadata flags and **no** Cohere rerank request (`reranker=None`). `/api/v1/rag/` and `/api/query/` pass `reranker="cohere"`; without an API key that step is a no-op.

## Stages that run

| Stage | Implementation | Notes |
| --- | --- | --- |
| Ingestion / chunking | Offline / indexing scripts | Not on each HTTP query. Demo eval uses basic chunking (not EnhancedChunker). |
| BM25 | SQLite FTS5 | Live. Failure → empty list, pipeline continues. |
| Vector | Weaviate `nearVector` | Live when enabled. Runtime `require_vector=False`; failure → BM25-only. |
| Fusion | `score_fuse` then `rrf_combine` | Weighted fusion first; RRF is the exception path. |
| Cross-encoder | `sentence-transformers` | Default on in `search_hybrid`; skipped if the library/model path fails. |
| Provider rerank | Cohere or Jina | Only if requested **and** keyed. Metadata distinguishes requested vs applied. |
| Packing | `pack_contexts` | Token budget, per-source cap, dedupe. |
| Generation | `llm_generate` | Azure OpenAI preferred, else OpenAI. Missing credentials → error, not a stub answer. |

**MMR is not applied** on this path. `use_mmr` on `search_hybrid` is unused. A legacy retrieve helper still calls MMR and is not used by `generate_answer`. `MMR_LAMBDA` in `env.template` does not change live ranking.

Prompt builder versions exist in code; the live default is **v1.1**. Discord-specific prompt builders are not wired into `generate_answer`.

## Failure semantics

- Retrieval/provider/generation failures are **not** converted to mock answers.
- Public HTTP errors are sanitized (typical RAG failure: **503** with a generic message).
- Empty retrieval can still reach the LLM; that is not the same as a mocked answer.
- Embeddings may fall back to zero vectors if the embedding provider is missing — vector quality then degrades. That is a limitation, not a feature.

## Indexing vs serving

| Path | When |
| --- | --- |
| Demo indexer | `make eval-rag-demo` — SQLite/FTS only |
| `rag_agent/indexing/` | Scripts for a Weaviate-enabled hybrid index |
| HTTP handlers | Retrieval + generation only |

## Evaluation

Retrieval ranking only. See [`rag_agent/evaluation/README.md`](../rag_agent/evaluation/README.md). Demo: 6 documents, 8 gold cases, BM25, CI-gated smoke thresholds — not a generation benchmark.

## Config that is easy to over-read

```bash
DEFAULT_TOP_K=5
MAX_TOP_K=20
BM25_WEIGHT=0.4
VECTOR_WEIGHT=0.6
MMR_LAMBDA=0.65   # leftover for live generate_answer
```

Fusion weights are used. `MMR_LAMBDA` is not, on the live path.
