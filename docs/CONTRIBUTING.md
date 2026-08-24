# Contributing

This repository is a local-first RAG portfolio. Changes should stay consistent with **CI**, not with a deployment pipeline (there is none).

## Setup

```bash
cp env.template .env
make install
make env-check
```

Python **3.11** and Node **20** match [`.github/workflows/main.yml`](../.github/workflows/main.yml).

## Checks to run locally

```bash
make lint
make format-check
make test
make eval-rag-demo
```

Backend/RAG: Poetry, isort, Ruff, pytest. Frontend: npm, Prettier, ESLint, Jest.

## CI job names

PRs to `main` are expected to pass:

- Backend (FastAPI)
- RAG Agent Pipeline
- Frontend (React/Next.js)
- Docker Build
- Backend Security Scan (Bandit high/high)

`Integration Check` is an aggregate job. The **Protect main** ruleset requires the five named jobs, not the aggregate.

Bandit scans **`backend/app` only**. High severity + high confidence findings fail the job. The full JSON artifact is informational.

Docker Build builds images with **push: false**. It is not a release/CD step.

## Style

Follow existing Ruff/isort/Prettier settings. Do not add a second formatter stack (Black, YAPF, flake8) to CI.

## Pull requests

- Keep behavior changes covered by tests in the same PR when practical.
- Do not treat leftover config (`MMR_LAMBDA`, unused modules) as live features in docs.
- Do not add production/Kubernetes/auth claims unless the code exists.
