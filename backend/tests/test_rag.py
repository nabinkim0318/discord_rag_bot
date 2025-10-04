import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_query_rag_success(client):
    payload = {
        "query": "What is Retrieval-Augmented Generation?",
        "top_k": 3,
        "use_streaming": False,
    }

    response = client.post("/api/v1/rag/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data.get("answer"), str)
    assert isinstance(data.get("contexts"), list)
    assert len(data["contexts"]) > 0
    assert isinstance(data.get("metadata"), dict)


# @pytest.mark.parametrize(
#     "payload, expected_status",
#     [
#         ({"top_k": 3, "use_streaming": False}, 422),  # query is missing
#         ({"query": "test", "top_k": "not_a_number"}, 422),  # invalid type
#         ({"query": "test", "top_k": -1}, 422),  # out of range
#     ],
# )

# def test_query_rag_failure_cases(client, payload, expected_status):
#     # response = client.post("/api/v1/rag/", json=payload)
#     # assert response.status_code == expected_status
#     # data = response.json()
#     # # Check for new error response format
#     # assert "error" in data
#     # assert "error_code" in data
#     # assert "message" in data
