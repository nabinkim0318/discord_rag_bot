# Testing

Run tests with Make. Do not treat pass counts in old notes as current.

```bash
make test              # backend + rag_agent + frontend
make test-backend
make test-rag
make test-frontend
make eval-rag-demo     # retrieval smoke eval (also in CI)
```

## Layout

| Area | Location | Runner |
| --- | --- | --- |
| FastAPI | `backend/tests/` | `poetry run pytest` |
| RAG library | `rag_agent/tests/` | `poetry run pytest` |
| Next.js | `frontend/__tests__/` | Jest |
| Demo retrieval eval | `rag_agent/evaluation/` | `make eval-rag-demo` |

CI job **RAG Agent Pipeline** runs rag_agent pytest **and** `make eval-rag-demo`.

`make eval-rag-hybrid` is optional and not in CI.

## What eval is not

`make eval-rag-demo` scores **ranked chunk UIDs** against gold. It does not measure generated-answer quality, faithfulness, or prompt versions.

For CI job names see [CONTRIBUTING.md](CONTRIBUTING.md) and the root README.
