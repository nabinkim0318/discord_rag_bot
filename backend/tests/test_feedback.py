# from fastapi.testclient import TestClient

# from app.main import app

# client = TestClient(app)

# def test_submit_feedback_success():
#     payload = {
#         "query": "What is RAG?",
#         "answer": "RAG stands for Retrieval-Augmented Generation...",
#         "feedback_type": "like",
#         "comment": "This was helpful!",
#     }

#     response = client.post("/api/v1/feedback/", json=payload)
#     assert response.status_code == 200
#     data = response.json()
#     assert data["status"] == "success"
#     assert "message" in data
