# app/core/metrics.py
"""
Prometheus metric setup
"""

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize Prometheus FastAPI Instrumentator
instrumentator = Instrumentator()

# ==================== RAG related metrics ====================

# Total number of RAG queries
rag_query_counter = Counter(
    "rag_query_total", "Total number of RAG queries", ["method", "endpoint"]
)

# Number of failed RAG queries
rag_query_failures = Counter(
    "rag_query_failures", "Number of failed RAG queries", ["endpoint", "error_type"]
)

# Distribution of RAG query processing time
rag_query_latency = Histogram(
    "rag_query_latency_seconds", "Latency for RAG queries", ["endpoint"]
)

# ==================== Feedback related metrics ====================

# Total number of feedbacks
feedback_counter = Counter(
    "feedback_total", "Total number of feedbacks received", ["type"]
)

# ==================== Health check related metrics ====================

# Total number of health checks
health_check_counter = Counter(
    "health_check_total", "Total number of health checks", ["status"]
)

# Database health check
health_check_db_counter = Counter(
    "health_check_db_total", "Total number of database health checks", ["status"]
)

health_check_db_failures = Counter(
    "health_check_db_failures", "Number of database health check failures"
)

health_check_db_latency = Histogram(
    "health_check_db_latency_seconds", "Database health check latency"
)

# LLM health check
health_check_llm_counter = Counter(
    "health_check_llm_total", "Total number of LLM health checks", ["status"]
)

health_check_llm_failures = Counter(
    "health_check_llm_failures", "Number of LLM health check failures"
)

health_check_llm_latency = Histogram(
    "health_check_llm_latency_seconds", "LLM health check latency"
)

# Vector store health check
health_check_vector_store_counter = Counter(
    "health_check_vector_store_total",
    "Total number of vector store health checks",
    ["status"],
)

health_check_vector_store_failures = Counter(
    "health_check_vector_store_failures", "Number of vector store health check failures"
)

health_check_vector_store_latency = Histogram(
    "health_check_vector_store_latency_seconds", "Vector store health check latency"
)

# ==================== Metric functions ====================


def rag_query_metric(info):
    """RAG endpoint tracking logic"""
    path = info.scope.get("path", "")
    if path in ["/api/v1/rag/", "/api/query/"]:
        rag_query_counter.labels(method=info.method, endpoint=path).inc()
        rag_query_latency.labels(endpoint=path).observe(info.duration)


def record_feedback_metric(feedback_type: str):
    """Record feedback metric"""
    feedback_counter.labels(type=feedback_type).inc()


def record_failure_metric(endpoint: str, error_type: str):
    """Record failed request metric"""
    rag_query_failures.labels(endpoint=endpoint, error_type=error_type).inc()


# Register metrics with Instrumentator
instrumentator.add(rag_query_metric)
