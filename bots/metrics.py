# bots/metrics.py
"""
Simple metrics for Discord bot
"""
from typing import Any, Dict

# Simple in-memory metrics storage
_metrics: Dict[str, Any] = {
    "rag_total": 0,
    "rag_failures": 0,
    "rag_latency": [],
}


def increment_rag_total():
    """Increment total RAG requests"""
    _metrics["rag_total"] += 1


def increment_rag_failures():
    """Increment RAG failures"""
    _metrics["rag_failures"] += 1


def record_rag_latency(latency: float):
    """Record RAG latency"""
    _metrics["rag_latency"].append(latency)
    # Keep only last 100 measurements
    if len(_metrics["rag_latency"]) > 100:
        _metrics["rag_latency"] = _metrics["rag_latency"][-100:]


def get_metrics() -> Dict[str, Any]:
    """Get current metrics"""
    latency_list = _metrics["rag_latency"]
    avg_latency = sum(latency_list) / len(latency_list) if latency_list else 0

    return {
        "rag_total": _metrics["rag_total"],
        "rag_failures": _metrics["rag_failures"],
        "rag_success_rate": (_metrics["rag_total"] - _metrics["rag_failures"])
        / max(_metrics["rag_total"], 1),
        "rag_avg_latency": avg_latency,
    }


# For compatibility with bot.py
RAG_TOTAL = _metrics["rag_total"]
RAG_FAILURES = _metrics["rag_failures"]
RAG_LATENCY = _metrics["rag_latency"]
