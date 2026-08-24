from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import RAGException
from app.main import app


def test_health_root():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data or isinstance(data, dict)


def test_health_db():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health/db")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "duration" in data


def test_health_llm():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health/llm")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "duration" in data
        assert data["probe"] == "not_performed"


def test_health_vector_store():
    with (
        patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
        TestClient(app) as client,
    ):
        mock_client = MagicMock()
        mock_client.health_check.return_value = True
        mock_get_client.return_value = mock_client
        resp = client.get("/api/v1/health/vector-store")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "duration" in data


def test_query_endpoint_mock(monkeypatch):
    import app.api.query as query_router

    def fake_run_rag_pipeline(query: str, top_k: int = 5, **kwargs):
        return "mock-answer", ["ctx1", "ctx2"], {"num_contexts": 2}

    monkeypatch.setattr(query_router, "run_rag_pipeline", fake_run_rag_pipeline)

    payload = {"query": "hello", "top_k": 3}
    with TestClient(app) as client:
        resp = client.post("/api/query/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "mock-answer"
        assert data["contexts"] == ["ctx1", "ctx2"]


def test_query_endpoint_failure_records_metric_and_returns_503(monkeypatch):
    import app.api.query as query_router

    pipeline_error = RAGException(
        "internal retrieval detail",
        error_code="RAG_RETRIEVAL_ERROR",
        details={"stage": "retrieval"},
    )

    def failing_pipeline(*args, **kwargs):
        raise pipeline_error

    monkeypatch.setattr(query_router, "run_rag_pipeline", failing_pipeline)

    with (
        patch("app.api.query.record_failure_metric") as mock_failure_metric,
        TestClient(app) as client,
    ):
        response = client.post(
            "/api/query/",
            json={"query": "failing query", "top_k": 3},
        )

    assert response.status_code == 503
    assert "internal retrieval detail" not in response.text
    mock_failure_metric.assert_called_once_with("/api/query/", "RAG_RETRIEVAL_ERROR")
