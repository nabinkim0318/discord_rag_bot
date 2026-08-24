# Local Docker Compose

Root [`docker-compose.yaml`](../docker-compose.yaml) is a **local/portfolio topology**. It is not a production deployment. Published ports bind to **127.0.0.1**.

The RAG library runs **inside the API container**. There is no separate `rag_agent` Compose service at runtime.

## Environment

```bash
cp env.template .env
```

The template file is **`env.template`**.

Set at least:

- `OPENAI_API_KEY`
- `SECRET_KEY`
- `GRAFANA_ADMIN_PASSWORD` (Compose has **no** default Grafana password)

Optional:

- `DISCORD_BOT_TOKEN` — required only if you start the bot profile
- `WEAVIATE_API_KEY` — defaults to `local-dev-weaviate-api-key` in Compose and the template (local-dev only)
- `GRAFANA_ADMIN_USER` — defaults to `admin` if unset

```bash
make env-check
```

## Commands

```bash
make docker-build
make docker-up              # weaviate, api, frontend, prometheus, grafana
make docker-up-with-bot     # plus bot + Discord scrape overlay
make docker-logs
make docker-logs-api
make docker-logs-bot        # useful only when the bot profile is up
make docker-down
make docker-clean           # down + volumes
```

Equivalent Compose:

```bash
docker compose up -d
docker compose --profile discord -f docker-compose.yaml -f docker-compose.discord.yaml up -d
```

`bot` uses Compose **profile `discord`**. `docker compose up -d bot` without `--profile discord` does not start it.

Do not scale `api` with `--scale api=2`. This topology is single-instance and loopback-bound.

## Services

| Service | Host port | Healthcheck |
| --- | --- | --- |
| `weaviate` | `127.0.0.1:8080` | `GET /v1/.well-known/ready` |
| `api` | `127.0.0.1:8001` | `GET /api/v1/health/livez` |
| `frontend` | `127.0.0.1:3000` | none |
| `prometheus` | `127.0.0.1:9090` | none |
| `grafana` | `127.0.0.1:3001` | none |
| `bot` | none | none (profile `discord`) |

Networks: `app_net` (`discord_rag_network`), `monitoring` (`monitoring_network`).

Weaviate: API-key auth enabled, anonymous access **off** by default. The API container must use the same `WEAVIATE_API_KEY`.

SQLite for the API is configured via `DATABASE_URL`. Compose does **not** start PostgreSQL.

## URLs

| URL | What |
| --- | --- |
| http://127.0.0.1:3000 | Frontend |
| http://127.0.0.1:8001 | API |
| http://127.0.0.1:8001/docs | OpenAPI |
| http://127.0.0.1:8001/metrics | Prometheus scrape (API) |
| http://127.0.0.1:8080 | Weaviate |
| http://127.0.0.1:9090 | Prometheus UI |
| http://127.0.0.1:3001 | Grafana |

Grafana login: `GRAFANA_ADMIN_USER` (default `admin`) and **`GRAFANA_ADMIN_PASSWORD` from `.env`**. There is no committed `admin/admin` password.

Discord bot metrics (`bot:9109`) are scraped only when [`docker-compose.discord.yaml`](../docker-compose.discord.yaml) is applied.

## Health vs readiness

Compose marks `api` healthy on **liveness** (`/livez`). Dependency readiness is `/api/v1/health/readyz` (SQLite + Weaviate) and is **not** the Compose healthcheck.

```bash
curl -f http://127.0.0.1:8001/api/v1/health/livez
curl -f http://127.0.0.1:8001/api/v1/health/readyz
curl -f http://127.0.0.1:8080/v1/.well-known/ready
```
