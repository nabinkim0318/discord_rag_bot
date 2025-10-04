"""
Prometheus metric setup
"""

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize Prometheus FastAPI Instrumentator
instrumentator = Instrumentator()

# ==================== Metric Helper Functions ====================


def create_counter(name: str, description: str, labels: list[str] = None):
    return Counter(name, description, labelnames=labels or [])


def create_histogram(name: str, description: str, labels: list[str] = None):
    return Histogram(name, description, labelnames=labels or [])


def create_gauge(name: str, description: str, labels: list[str] = None):
    return Gauge(name, description, labelnames=labels or [])


# ==================== RAG Metrics ====================

rag_query_counter = create_counter(
    "rag_query_total", "Total number of RAG queries", ["method", "endpoint"]
)

rag_query_failures = create_counter(
    "rag_query_failures", "Number of failed RAG queries", ["endpoint", "error_type"]
)

rag_query_latency = create_histogram(
    "rag_query_latency_seconds", "Latency for RAG queries", ["endpoint"]
)

# Additional RAG metrics
rag_pipeline_latency = create_histogram(
    "rag_pipeline_latency_seconds",
    "End-to-end RAG pipeline latency (retrieval + generation)",
)

rag_retrieval_hit_counter = create_counter(
    "rag_retrieval_hits_total",
    "RAG retrieval hit outcomes (whether any contexts were found)",
    ["hit"],
)

rag_retriever_topk = create_histogram(
    "rag_retriever_topk",
    "Distribution of requested top_k values for retrieval",
)

# ==================== Feedback Metrics ====================

feedback_counter = create_counter(
    "feedback_total", "Total number of feedbacks received", ["type"]
)

feedback_submissions = create_counter(
    "feedback_submissions_total", "Total number of feedback submissions", ["score"]
)

feedback_satisfaction_rate = create_gauge(
    "feedback_satisfaction_rate", "User satisfaction rate (up votes / total votes)"
)

# ==================== Request Metrics ====================

rag_requests_total = create_counter(
    "rag_requests_total", "Total number of RAG requests", ["endpoint"]
)

rag_failures_total = create_counter(
    "rag_failures_total", "Total number of RAG failures", ["endpoint", "error_type"]
)

# ==================== Circuit Breaker Metrics ====================

circuit_breaker_state = create_gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service"],
)

# ==================== Health Check Metrics ====================

# General health check
health_check_counter = create_counter(
    "health_check_total", "Total number of health checks", ["status"]
)

# Database
health_check_db_counter = create_counter(
    "health_check_db_total", "Total number of database health checks", ["status"]
)

health_check_db_failures = create_counter(
    "health_check_db_failures", "Number of database health check failures"
)

health_check_db_latency = create_histogram(
    "health_check_db_latency_seconds", "Database health check latency"
)

# LLM
health_check_llm_counter = create_counter(
    "health_check_llm_total", "Total number of LLM health checks", ["status"]
)

health_check_llm_failures = create_counter(
    "health_check_llm_failures", "Number of LLM health check failures"
)

health_check_llm_latency = create_histogram(
    "health_check_llm_latency_seconds", "LLM health check latency"
)

# Vector Store
health_check_vector_store_counter = create_counter(
    "health_check_vector_store_total",
    "Total number of vector store health checks",
    ["status"],
)

health_check_vector_store_failures = create_counter(
    "health_check_vector_store_failures", "Number of vector store health check failures"
)

health_check_vector_store_latency = create_histogram(
    "health_check_vector_store_latency_seconds", "Vector store health check latency"
)

# ==================== Metric Recording Functions ====================


def rag_query_metric(info):
    """RAG endpoint tracking logic"""
    path = getattr(info, "modified_path", None) or getattr(info, "path", "")
    method = getattr(info, "method", "")
    duration = getattr(info, "duration", getattr(info, "latency", 0.0))

    if path in ["/api/v1/rag/", "/api/query/"]:
        rag_query_counter.labels(method=method, endpoint=path).inc()
        rag_query_latency.labels(endpoint=path).observe(duration)


def record_feedback_metric(feedback_type: str):
    """Record feedback metric"""
    feedback_counter.labels(type=feedback_type).inc()


def record_failure_metric(endpoint: str, error_type: str):
    """Record failed request metric"""
    rag_query_failures.labels(endpoint=endpoint, error_type=error_type).inc()
    rag_failures_total.labels(endpoint=endpoint, error_type=error_type).inc()


def record_rag_request(endpoint: str):
    """Record RAG request metric"""
    rag_requests_total.labels(endpoint=endpoint).inc()


def record_rag_pipeline_latency(seconds: float):
    """Record end-to-end pipeline latency in seconds"""
    rag_pipeline_latency.observe(seconds)


def record_retrieval_hit(hit: bool):
    """Record whether retrieval returned at least one result"""
    rag_retrieval_hit_counter.labels(hit="true" if hit else "false").inc()


def record_retriever_topk(top_k: int):
    """Record distribution of requested top_k values"""
    try:
        rag_retriever_topk.observe(float(top_k))
    except Exception:
        # Histogram expects numeric values; ignore invalid inputs safely
        pass


def record_prompt_version(prompt_version: str):
    """Record prompt version usage"""
    # For now, just a placeholder function
    # Could be implemented as a counter if needed
    pass


# Register metrics with Instrumentator
instrumentator.add(rag_query_metric)
