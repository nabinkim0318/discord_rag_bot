# app/core/metrics.py
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()

# Custom Counter for /api/v1/rag
rag_query_counter = Counter(
    "rag_query_total", "Total number of RAG queries", ["method", "endpoint"]
)


def rag_query_metric(request):
    if request.url.path == "/api/v1/rag/":
        rag_query_counter.labels(method=request.method, endpoint=request.url.path).inc()


instrumentator.add(rag_query_metric)
