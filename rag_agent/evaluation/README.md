# Retrieval evaluation

This package scores **ranked chunk UIDs**, not generated answers.
It does not measure faithfulness, citation quality, or LLM output.

## Demo corpus

Synthetic public documents live in `rag_agent/demo/corpus/`.
They contain no Discord messages, user IDs, secrets, or private files.

Gold labels are in `rag_agent/demo/gold.jsonl`. Each line is:

```json
{"qid": "q1", "question": "...", "relevant_uids": ["doc_id#0"]}
```

Labels were assigned from the document text, not from retrieval output.
UIDs use the indexer contract `doc_id#chunk_id`.

## Public command

After `make install-rag` (or `poetry install` in `rag_agent/`):

```bash
make eval-rag-demo
```

That command:

1. Recreates `rag_agent/.demo/demo_kb.sqlite3` from the committed corpus
2. Validates gold JSONL and that every `relevant_uids` exists in sqlite
3. Runs BM25/FTS retrieval only (`--mode bm25`)
4. Prints a summary and exits 0 only if the smoke gates pass

It does not need `.env`, OpenAI, Weaviate, Docker, Postgres, or Discord.
Package install may still use a package index; evaluation itself does not
call external services.

Index only:

```bash
make eval-rag-demo-index
```

## BM25 vs hybrid

| Mode | What runs | Services |
| --- | --- | --- |
| `bm25` / demo | sqlite FTS BM25 | none |
| `hybrid` | sqlite + Weaviate/vector | configured Weaviate and embeddings |

Demo evaluation **always** uses `--mode bm25`. It does not fall back to BM25
after a Weaviate error; vector search is not invoked.

Optional hybrid evaluation (not in CI):

```bash
make eval-rag-hybrid EVAL_GOLD=... EVAL_SQLITE=...
```

If Weaviate or embeddings are missing, hybrid mode fails with a prerequisite
error. It does not silently report a hybrid run.

## Artifacts

Generated files go to `rag_agent/.demo/evaluation_results/` (gitignored):

- `cases_<timestamp>.jsonl`
- `summary_<timestamp>.json`
- `evaluation_metrics.json`

Timestamps in filenames and wall-clock latency are not part of the
reproducible claim.

## Smoke thresholds

These gates are a reproducibility smoke test, not a retrieval benchmark.

- hit rate ≥ 0.8
- nDCG@k ≥ 0.5
- latency is recorded and is **not** a pass/fail gate

Rationale: the corpus is small and topically separated, so BM25 should
return the labeled chunk for lexical queries. Thresholds are below a
perfect score on purpose. They are not evidence of production quality.

## Reproducibility limits

Repeated `make eval-rag-demo` on the same checkout should match:

- case count
- gold UIDs
- ranked UIDs
- ranking metrics (p/r/nDCG/MRR/MAP/hit rate)
- PASS/FAIL

They will not match wall-clock latency, timestamps, or artifact filenames.

Queries are lexical because sqlite FTS5 MATCH is conjunctive: every token
must appear in the chunk. Natural-language function words (e.g. "What")
are absent from the corpus and would make MATCH return nothing. That is a
property of the current BM25 matcher, not a hidden hybrid fallback.

Do not treat demo scores as production-grade or benchmark-quality.
