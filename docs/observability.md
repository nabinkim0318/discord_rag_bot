# Observability & Metrics

## Metric Naming Guide

| Metric | Source | Meaning | Labels |
|---|---|---|---|
| rag_query_total | backend | Count of RAG queries handled by API | method, endpoint |
| rag_query_latency_seconds | backend | Histogram for RAG query latency | endpoint, le |
| rag_query_failures | backend | Failed RAG requests | endpoint, error_type |
| rag_requests_total | backend | Generic count of all `/api/*` requests | endpoint |
| feedback_submissions_total | backend | Count of feedback submissions | score |
| feedback_satisfaction_rate | backend | Gauge: up / total | - |
| discord_feedback_clicks_total | bot | Count of button clicks | type |
| discord_slash_invocations_total | bot | Slash command invocations | command |

- Prefer `*_total` for counters, `*_seconds` for latency histograms, and explicit labels.
- Avoid overlapping counters that represent the same concept;
  prefer `rag_query_total` for query semantics and `rag_requests_total` for raw API visibility.

## Dashboards

- RAG Bot Core Metrics Dashboard (default home)
  - Request Rate by Endpoint, Query Latency p95, Failure Rate
  - Feedback Submission Rate, Satisfaction, Discord Feedback Clicks (2m)

## Alerting (suggested)

- p95 latency > threshold for N minutes
- Failure rate > X% for N minutes
- Feedback submissions drop to zero for N minutes
