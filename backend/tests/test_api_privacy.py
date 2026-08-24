"""API correctness, privacy, and request-ID tests for PR 6."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

import pytest
from db_test_utils import create_memory_engine
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.logging import logger
from app.db.session import get_session
from app.main import app
from app.models.query import Query
from app.models.rag import RAGQueryRequest

SENTINEL_PROMPT = "SENTINEL_PROMPT_DRAG_OBS_004"
SENTINEL_ANSWER = "SENTINEL_ANSWER_DRAG_OBS_004"
SENTINEL_USER = "SENTINEL_USER_ID_DRAG_OBS_004"
SENTINEL_CHANNEL = "SENTINEL_CHANNEL_ID_DRAG_OBS_004"
SENTINEL_SECRET = "SENTINEL_INTERNAL_EXCEPTION_SECRET"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_client():
    engine = create_memory_engine()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        yield TestClient(app), engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def _capture_logs():
    records: list[str] = []

    def _sink(message):
        records.append(str(message))

    handler_id = logger.add(_sink, level="INFO")
    return records, handler_id


def _mock_pipeline_result():
    return (
        SENTINEL_ANSWER,
        ["context snippet"],
        {"retrieval": {"reranker": None}},
    )


def test_query_rejects_empty_and_whitespace(client):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.api.v1.rag.run_rag_pipeline", lambda *a, **k: _mock_pipeline_result()
        )
        empty = client.post("/api/v1/rag/", json={"query": "", "top_k": 1})
        whitespace = client.post("/api/v1/rag/", json={"query": "   ", "top_k": 1})

    assert empty.status_code == 422
    assert whitespace.status_code == 422


def test_query_length_bounds(client):
    called = {"count": 0}

    def _pipeline(query, *args, **kwargs):
        called["count"] += 1
        return _mock_pipeline_result()

    exact = "a" * settings.MAX_QUERY_LENGTH
    too_long = "a" * (settings.MAX_QUERY_LENGTH + 1)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.v1.rag.run_rag_pipeline", _pipeline)
        ok = client.post("/api/v1/rag/", json={"query": exact, "top_k": 1})
        rejected = client.post("/api/v1/rag/", json={"query": too_long, "top_k": 1})

    assert ok.status_code == 200
    assert rejected.status_code == 422
    assert called["count"] == 1


@pytest.mark.parametrize(
    "top_k, expected",
    [
        (1, 200),
        (settings.MAX_TOP_K, 200),
        (settings.MAX_TOP_K + 1, 422),
        (0, 422),
        (-1, 422),
    ],
)
def test_top_k_bounds(client, top_k, expected):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.api.v1.rag.run_rag_pipeline", lambda *a, **k: _mock_pipeline_result()
        )
        response = client.post(
            "/api/v1/rag/",
            json={"query": "bounded top_k question", "top_k": top_k},
        )
    assert response.status_code == expected
    if expected == 422:
        assert "SENTINEL" not in response.text


def test_invalid_query_does_not_invoke_pipeline(client):
    called = {"count": 0}

    def _pipeline(*args, **kwargs):
        called["count"] += 1
        return _mock_pipeline_result()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.v1.rag.run_rag_pipeline", _pipeline)
        mp.setattr("app.api.v1.enhanced_rag.run_enhanced_rag_pipeline", _pipeline)
        mp.setattr("app.api.query.run_rag_pipeline", _pipeline)
        client.post("/api/v1/rag/", json={"query": " ", "top_k": 1})
        client.post("/api/v1/enhanced-rag/", json={"query": "", "top_k": 1})
        client.post("/api/query/", json={"query": "ok", "top_k": 0})

    assert called["count"] == 0


def test_rag_routes_are_sync_threadpool_handlers():
    sync_paths = {"/api/v1/rag/", "/api/v1/enhanced-rag/", "/api/query/"}
    found = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in sync_paths and "POST" in methods:
            assert not inspect.iscoroutinefunction(route.endpoint)
            found.add(path)
    assert found == sync_paths


def test_server_generates_request_id(client):
    captured = {}

    def _pipeline(query, top_k, *, request_id=None, **kwargs):
        captured["request_id"] = request_id
        return _mock_pipeline_result()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.v1.rag.run_rag_pipeline", _pipeline)
        response = client.post("/api/v1/rag/", json={"query": "hello", "top_k": 1})

    assert response.status_code == 200
    header_id = response.headers.get("X-Request-ID")
    UUID(header_id)
    assert captured["request_id"] == header_id
    body_id = response.json().get("request_id")
    assert body_id in (None, header_id)


def test_valid_caller_request_id_is_propagated(client):
    caller_id = str(uuid4())
    captured = {}

    def _pipeline(query, top_k, *, request_id=None, **kwargs):
        captured["request_id"] = request_id
        return _mock_pipeline_result()

    records, handler_id = _capture_logs()
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.api.v1.rag.run_rag_pipeline", _pipeline)
            response = client.post(
                "/api/v1/rag/",
                json={"query": "hello", "top_k": 1},
                headers={"X-Request-ID": caller_id},
            )
    finally:
        logger.remove(handler_id)

    assert response.headers.get("X-Request-ID") == caller_id
    assert captured["request_id"] == caller_id
    assert any(caller_id in line for line in records)


def test_malformed_and_oversized_request_ids_are_replaced(client):
    captured = {}

    def _pipeline(query, top_k, *, request_id=None, **kwargs):
        captured["request_id"] = request_id
        return _mock_pipeline_result()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.v1.rag.run_rag_pipeline", _pipeline)
        malformed = client.post(
            "/api/v1/rag/",
            json={"query": "hello", "top_k": 1},
            headers={"X-Request-ID": "not-a-uuid"},
        )
        oversized = client.post(
            "/api/v1/rag/",
            json={"query": "hello", "top_k": 1},
            headers={"X-Request-ID": "x" * 200},
        )

    for response in (malformed, oversized):
        header_id = response.headers.get("X-Request-ID")
        UUID(header_id)
        assert header_id != "not-a-uuid"
        assert len(header_id) <= 64


def test_query_history_is_not_publicly_enumerable(db_client):
    client, engine = db_client
    with Session(engine) as session:
        session.add(
            Query(
                user_id=SENTINEL_USER,
                query=SENTINEL_PROMPT,
                answer=SENTINEL_ANSWER,
                context={"contexts": ["secret-context"]},
            )
        )
        session.commit()

    response = client.get("/api/query/queries/")
    assert response.status_code == 404
    assert SENTINEL_PROMPT not in response.text
    assert SENTINEL_ANSWER not in response.text
    assert SENTINEL_USER not in response.text


def test_feedback_history_is_not_public(client):
    response = client.get(f"/api/v1/feedback/history/{SENTINEL_USER}")
    assert response.status_code == 404
    assert SENTINEL_PROMPT not in response.text
    assert "question" not in response.text.lower() or response.status_code == 404


def test_feedback_summary_has_no_prompt_content(client):
    response = client.get("/api/v1/feedback/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "question" not in payload
    assert "response" not in payload
    assert "user_id" not in payload


def test_sentinel_values_absent_from_normal_logs(client):
    records, handler_id = _capture_logs()
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.api.v1.rag.run_rag_pipeline",
                lambda *a, **k: _mock_pipeline_result(),
            )
            mp.setattr(
                "app.api.query.run_rag_pipeline",
                lambda *a, **k: _mock_pipeline_result(),
            )
            client.post(
                "/api/v1/rag/",
                json={"query": SENTINEL_PROMPT, "top_k": 1, "user_id": SENTINEL_USER},
                headers={
                    "X-User-ID": SENTINEL_USER,
                    "X-Channel-ID": SENTINEL_CHANNEL,
                },
            )
    finally:
        logger.remove(handler_id)

    combined = "\n".join(records)
    assert SENTINEL_PROMPT not in combined
    assert SENTINEL_ANSWER not in combined
    assert SENTINEL_USER not in combined
    assert SENTINEL_CHANNEL not in combined


def test_public_errors_omit_internal_exception_text(client):
    def _boom(*args, **kwargs):
        raise RuntimeError(SENTINEL_SECRET)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.api.v1.feedback.feedback_service.submit_feedback",
            _boom,
        )
        response = client.post(
            "/api/v1/feedback/submit",
            json={"message_id": str(uuid4()), "score": "up"},
        )

    assert response.status_code == 500
    assert SENTINEL_SECRET not in response.text
    assert response.json()["message"] == "A database error occurred"


def test_provider_failure_still_returns_sanitized_503(client):
    error = ExternalServiceException(
        "provider secret: invalid credential",
        service_name="llm-provider",
    )

    def _fail(*args, **kwargs):
        raise error

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.v1.rag.run_rag_pipeline", _fail)
        response = client.post(
            "/api/v1/rag/", json={"query": "Trigger provider failure", "top_k": 3}
        )

    assert response.status_code == 503
    assert "provider secret" not in response.text
    assert response.json()["message"] == "RAG dependency is temporarily unavailable"


def test_store_rag_result_helper_removed():
    import app.services.rag_service as rag_service

    assert not hasattr(rag_service, "store_rag_result_in_weaviate")


def test_use_streaming_is_not_a_public_field():
    assert "use_streaming" not in RAGQueryRequest.model_fields
    assert RAGQueryRequest.model_fields["top_k"].default == settings.DEFAULT_TOP_K


def test_query_persistence_returns_query_id(db_client):
    client, _engine = db_client
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.api.query.run_rag_pipeline", lambda *a, **k: _mock_pipeline_result()
        )
        response = client.post(
            "/api/query/",
            json={"query": "persist this", "top_k": 1, "user_id": "discord-user"},
        )
    assert response.status_code == 200
    assert response.json()["query_id"]
