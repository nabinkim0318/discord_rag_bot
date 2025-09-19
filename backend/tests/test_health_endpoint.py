from fastapi.testclient import TestClient

from app.main import app


def test_health_root():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data or isinstance(data, dict)
        assert "duration" in data


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


def test_health_vector_store():
    with TestClient(app) as client:
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
