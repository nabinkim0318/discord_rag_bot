# Documentation

Guides for this repository. **Runtime code and Compose/CI config are authoritative** if a guide disagrees with them.

The root [README](../README.md) is the portfolio landing page. This folder is the longer-form index.

## Guides

| Guide | Contents |
| --- | --- |
| [DOCKER.md](DOCKER.md) | Local Compose: services, loopback binds, profiles, Make targets |
| [RAG_SYSTEM_GUIDE.md](RAG_SYSTEM_GUIDE.md) | Live retrieval/generation path (what actually runs) |
| [Retrieval evaluation](../rag_agent/evaluation/README.md) | `make eval-rag-demo` and optional hybrid eval |
| [DISCORD_BOT_GUIDE.md](DISCORD_BOT_GUIDE.md) | `interactions.py` bot, slash commands, feedback buttons |
| [observability.md](observability.md) | Prometheus metrics, Grafana panels, scrape targets |
| [TEST_STRUCTURE.md](TEST_STRUCTURE.md) | How to run tests (no frozen pass counts) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Lint, test, and CI job names |

Ops config lives in [`ops/`](../ops/) (Prometheus, Grafana). Compose files are at the repo root (`docker-compose.yaml`, `docker-compose.discord.yaml`).

## Source of truth

Prefer, in order: `backend/app/`, `rag_agent/`, `docker-compose.yaml`, `.github/workflows/main.yml`, then these guides.
