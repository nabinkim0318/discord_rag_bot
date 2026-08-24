# Observability

Authoritative sources: [`backend/app/core/metrics.py`](../backend/app/core/metrics.py), [`ops/prometheus/prometheus.yml`](../ops/prometheus/prometheus.yml), [`ops/grafana/provisioning/dashboards/rag-metrics-dashboard.json`](../ops/grafana/provisioning/dashboards/rag-metrics-dashboard.json).

The API exposes Prometheus metrics at **`/metrics`** when `METRICS_ENABLED` is true (default).

## Backend metrics

Prometheus client Counters that are not already `*_total` are scraped as `*_total`. Grafana uses the scraped names.

| Python name | Typical scrape name | Type | Meaning |
| --- | --- | --- | --- |
| `rag_query_total` | `rag_query_total` | counter | RAG queries (`method`, `endpoint`) |
| `rag_query_failures` | `rag_query_failures_total` | counter | Failed RAG queries (`endpoint`, `error_type`) |
| `rag_query_latency_seconds` | same + `_bucket/_sum/_count` | histogram | RAG handler latency (`endpoint`) |
| `rag_pipeline_latency_seconds` | same + histogram suffixes | histogram | End-to-end pipeline latency |
| `rag_retrieval_hits_total` | `rag_retrieval_hits_total` | counter | Retrieval hit/miss (`hit`) |
| `rag_retriever_topk` | `rag_retriever_topk_*` | histogram | Requested `top_k` |
| `feedback_total` | `feedback_total` | counter | Feedback events (`type`) |
| `feedback_submissions_total` | `feedback_submissions_total` | counter | Submissions (`score`) |
| `feedback_satisfaction_rate` | `feedback_satisfaction_rate` | gauge | up / total |
| `rag_requests_total` | `rag_requests_total` | counter | `/api/*` request count (`endpoint`) |
| `rag_failures_total` | `rag_failures_total` | counter | Failures (`endpoint`, `error_type`) |
| `circuit_breaker_state` | `circuit_breaker_state` | gauge | `0=closed, 1=half_open, 2=open` (`service`) |
| `health_check_total` | `health_check_total` | counter | Health checks (`status`) |
| `health_check_db_total` | `health_check_db_total` | counter | DB health (`status`) |
| `health_check_db_failures` | `health_check_db_failures_total` | counter | DB health failures |
| `health_check_db_latency_seconds` | histogram suffixes | histogram | DB health latency |
| `health_check_llm_total` | `health_check_llm_total` | counter | LLM health (`status`) |
| `health_check_llm_failures` | `health_check_llm_failures_total` | counter | LLM health failures |
| `health_check_llm_latency_seconds` | histogram suffixes | histogram | LLM health latency |
| `health_check_vector_store_total` | `health_check_vector_store_total` | counter | Vector-store health (`status`) |
| `health_check_vector_store_failures` | `health_check_vector_store_failures_total` | counter | Vector-store health failures |
| `health_check_vector_store_latency_seconds` | histogram suffixes | histogram | Vector-store health latency |

`prometheus_fastapi_instrumentator` is attached to the app; do not assume extra `http_requests_total` panels exist. The provisioned dashboard does **not** query HTTP request counters.

## Discord bot metrics

Exported on **9109** when the bot process starts the exporter (`bots/discord/bot.py`):

| Name | Type |
| --- | --- |
| `discord_slash_invocations_total` | counter (`command`) |
| `discord_feedback_clicks_total` | counter (`type`) |
| `discord_command_errors_total` | counter (`stage`) |
| `discord_ask_latency_seconds` | summary |

These are **not** on the provisioned Grafana dashboard. Prometheus scrapes them only with the Discord overlay.

## Grafana dashboard

Title: **RAG Bot Core Metrics Dashboard** (folder `RAG Bot`).

| Panel | PromQL (as provisioned) |
| --- | --- |
| RAG Pipeline Latency | `histogram_quantile(0.95\|0.50, sum(rate(rag_pipeline_latency_seconds_bucket[5m])) by (le))` |
| Retrieval Hit Rate | `sum(rate(rag_retrieval_hits_total{hit="true"}[5m])) / clamp_min(sum(rate(rag_retrieval_hits_total[5m])), 1)` |
| RAG Failure Rate | `(sum(rate(rag_query_failures_total[5m])) OR vector(0)) / clamp_min(sum(rate(rag_query_total[5m])), 1)` |
| RAG Request Rate by Endpoint | `sum(rate(rag_query_total[5m])) by (endpoint)` |
| Feedback Submission Rate | `sum(increase(feedback_submissions_total[2m])) by (score)` |
| User Satisfaction Rate | `feedback_satisfaction_rate` |
| Average Requested top_k | `sum(rate(rag_retriever_topk_sum[5m])) / sum(rate(rag_retriever_topk_count[5m]))` |
| Query Latency by Endpoint (p95) | `histogram_quantile(0.95, sum(rate(rag_query_latency_seconds_bucket[5m])) by (le, endpoint))` |

Panel color thresholds (for example hit-rate 0.95 / 0.80) are **dashboard styling**, not project SLOs.

## Example alerts (not SLOs)

Provisioned in [`ops/grafana/provisioning/alerting/alerts.yml`](../ops/grafana/provisioning/alerting/alerts.yml):

- **RAG p95 Latency High** — `histogram_quantile(0.95, sum(rate(rag_pipeline_latency_seconds_bucket[5m])) by (le))` greater than **5** for 5m
- **Retrieval Hit Rate Low** — hit rate less than **0.5** for 5m

Treat these as example local alerts.

## Prometheus scrape

Default [`ops/prometheus/prometheus.yml`](../ops/prometheus/prometheus.yml):

| Job | Target | Path |
| --- | --- | --- |
| `prometheus` | `localhost:9090` | default |
| `fastapi-backend` | `api:8001` | `/metrics` |
| `weaviate` | `weaviate:8080` | `/v1/metrics` |

Extra jobs load from `/etc/prometheus/scrape.d/*.yml`. Default Compose mounts an empty `ops/prometheus/scrape.d/`. [`docker-compose.discord.yaml`](../docker-compose.discord.yaml) replaces that directory with `ops/prometheus/scrape.d.discord/` (`job_name: discord-bot`, `bot:9109`).

Local URLs: Prometheus http://127.0.0.1:9090 — Grafana http://127.0.0.1:3001 (`GRAFANA_ADMIN_PASSWORD` required; user defaults to `admin`).
