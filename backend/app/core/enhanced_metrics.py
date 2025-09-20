# backend/app/core/enhanced_metrics.py
"""
Enhanced metrics system
- Intent-based search performance
- Query decomposition statistics
- Discord response quality
- User interaction patterns
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ==================== Enhanced RAG Metrics ====================

# Query decomposition metrics
query_decomposition_counter = Counter(
    "rag_query_decomposition_total",
    "Total number of query decompositions",
    ["intent", "requires_clarification"],
)

query_intent_distribution = Counter(
    "rag_query_intent_total",
    "Distribution of query intents",
    ["intent", "confidence_level"],
)

# Intent-based search performance
intent_retrieval_hit_rate = Gauge(
    "rag_intent_retrieval_hit_rate", "Hit rate for each intent type", ["intent"]
)

intent_retrieval_latency = Histogram(
    "rag_intent_retrieval_latency_seconds", "Retrieval latency by intent", ["intent"]
)

# Search result quality
retrieval_result_quality = Histogram(
    "rag_retrieval_result_quality",
    "Quality of retrieval results",
    ["intent", "quality_tier"],
)

# Discord response metrics
discord_response_sections = Histogram(
    "rag_discord_response_sections",
    "Number of sections in Discord responses",
    ["intent"],
)

discord_response_sources = Histogram(
    "rag_discord_response_sources", "Number of sources in Discord responses", ["intent"]
)

discord_uncertainty_warnings = Counter(
    "rag_discord_uncertainty_warnings_total",
    "Number of uncertainty warnings in responses",
    ["intent", "warning_type"],
)

# User interaction patterns
user_query_complexity = Histogram(
    "rag_user_query_complexity",
    "Complexity of user queries (number of intents)",
    ["complexity_level"],
)

clarification_requests = Counter(
    "rag_clarification_requests_total",
    "Number of clarification requests",
    ["clarification_type"],
)

# Response quality metrics
response_quality_score = Histogram(
    "rag_response_quality_score",
    "Quality score of responses",
    ["intent", "quality_level"],
)

# System performance metrics
enhanced_rag_pipeline_latency = Histogram(
    "rag_enhanced_pipeline_latency_seconds",
    "End-to-end enhanced RAG pipeline latency",
    ["intent", "pipeline_stage"],
)

enhanced_rag_throughput = Counter(
    "rag_enhanced_throughput_total", "Enhanced RAG throughput", ["intent", "status"]
)

# Error and failure metrics
enhanced_rag_errors = Counter(
    "rag_enhanced_errors_total",
    "Enhanced RAG errors",
    ["error_type", "intent", "stage"],
)

# Data quality metrics
document_coverage = Gauge(
    "rag_document_coverage", "Coverage of documents by intent", ["doc_type", "intent"]
)

chunk_quality_score = Histogram(
    "rag_chunk_quality_score",
    "Quality score of document chunks",
    ["doc_type", "chunk_type"],
)

# User satisfaction metrics (feedback-based)
user_satisfaction_by_intent = Histogram(
    "rag_user_satisfaction_by_intent",
    "User satisfaction by intent type",
    ["intent", "satisfaction_level"],
)

# Real-time monitoring metrics
active_queries = Gauge("rag_active_queries", "Number of active queries being processed")

queue_depth = Gauge("rag_queue_depth", "Depth of query processing queue")

# System information
rag_system_info = Info("rag_system_info", "Information about the RAG system")

# ==================== Utility Functions ====================


def record_query_decomposition(intent: str, requires_clarification: bool):
    """Record query decomposition"""
    query_decomposition_counter.labels(
        intent=intent, requires_clarification=str(requires_clarification)
    ).inc()


def record_intent_distribution(intent: str, confidence: float):
    """Record intent distribution"""
    confidence_level = (
        "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
    )
    query_intent_distribution.labels(
        intent=intent, confidence_level=confidence_level
    ).inc()


def record_intent_retrieval_hit_rate(intent: str, hit_rate: float):
    """Record intent-based retrieval hit rate"""
    intent_retrieval_hit_rate.labels(intent=intent).set(hit_rate)


def record_intent_retrieval_latency(intent: str, latency: float):
    """Record intent-based retrieval latency"""
    intent_retrieval_latency.labels(intent=intent).observe(latency)


def record_retrieval_quality(intent: str, quality_score: float):
    """Record retrieval quality"""
    quality_tier = (
        "high" if quality_score > 0.8 else "medium" if quality_score > 0.5 else "low"
    )
    retrieval_result_quality.labels(intent=intent, quality_tier=quality_tier).observe(
        quality_score
    )


def record_discord_response_metrics(
    intent: str, sections_count: int, sources_count: int
):
    """Record Discord response metrics"""
    discord_response_sections.labels(intent=intent).observe(sections_count)
    discord_response_sources.labels(intent=intent).observe(sources_count)


def record_uncertainty_warning(intent: str, warning_type: str):
    """Record uncertainty warning"""
    discord_uncertainty_warnings.labels(intent=intent, warning_type=warning_type).inc()


def record_user_query_complexity(intent_count: int):
    """Record user query complexity"""
    complexity_level = (
        "simple" if intent_count == 1 else "complex" if intent_count > 2 else "medium"
    )
    user_query_complexity.labels(complexity_level=complexity_level).observe(
        intent_count
    )


def record_clarification_request(clarification_type: str):
    """Record clarification request"""
    clarification_requests.labels(clarification_type=clarification_type).inc()


def record_response_quality(intent: str, quality_score: float):
    """Record response quality"""
    quality_level = (
        "high" if quality_score > 0.8 else "medium" if quality_score > 0.5 else "low"
    )
    response_quality_score.labels(intent=intent, quality_level=quality_level).observe(
        quality_score
    )


def record_enhanced_rag_latency(intent: str, stage: str, latency: float):
    """Record enhanced RAG latency"""
    enhanced_rag_pipeline_latency.labels(intent=intent, pipeline_stage=stage).observe(
        latency
    )


def record_enhanced_rag_throughput(intent: str, status: str):
    """Record enhanced RAG throughput"""
    enhanced_rag_throughput.labels(intent=intent, status=status).inc()


def record_enhanced_rag_error(error_type: str, intent: str, stage: str):
    """Record enhanced RAG error"""
    enhanced_rag_errors.labels(error_type=error_type, intent=intent, stage=stage).inc()


def record_document_coverage(doc_type: str, intent: str, coverage: float):
    """Record document coverage"""
    document_coverage.labels(doc_type=doc_type, intent=intent).set(coverage)


def record_chunk_quality(doc_type: str, chunk_type: str, quality_score: float):
    """Record chunk quality"""
    chunk_quality_score.labels(doc_type=doc_type, chunk_type=chunk_type).observe(
        quality_score
    )


def record_user_satisfaction(intent: str, satisfaction_score: float):
    """Record user satisfaction"""
    satisfaction_level = (
        "high"
        if satisfaction_score > 4
        else "medium" if satisfaction_score > 2 else "low"
    )
    user_satisfaction_by_intent.labels(
        intent=intent, satisfaction_level=satisfaction_level
    ).observe(satisfaction_score)


def set_active_queries(count: int):
    """Set active queries"""
    active_queries.set(count)


def set_queue_depth(depth: int):
    """Set queue depth"""
    queue_depth.set(depth)


def set_rag_system_info(version: str, model: str, last_updated: str):
    """Set RAG system information"""
    rag_system_info.info(
        {"version": version, "model": model, "last_updated": last_updated}
    )
