# 🔗 Discord RAG Bot - Backend API

This is the FastAPI-based backend service for the Discord RAG
Bot project. It handles API endpoints for querying the RAG agent,
receiving user feedback, logging, and metrics collection.

---

## 📂 Structure

backend/
├── app/ # Main FastAPI app
│ ├── api/ # API routes (v1)
│ ├── core/ # Config, logging, DB
│ ├── models/ # Pydantic schemas
│ ├── services/ # Business logic (RAG calls, feedback)
│ └── utils/ # Utility functions
├── tests/ # Unit tests
├── Dockerfile # (Optional) Containerization
├── pyproject.toml # Poetry project config
├── requirements.txt # Pip compatibility (optional)
└── README.md # Project documentation

---

## 🚀 Features

- REST API for querying RAG pipeline
- Feedback collection
- Metrics tracking with Prometheus
- Configurable via `.env` + Pydantic Settings
- Structured logging with Loguru

---

## ⚙️ Installation

```bash
# Install Python dependencies
poetry install --with dev

# Activate virtual environment
poetry shell
⚠️ If torch installation fails, install it separately:

pip install torch --index-url https://download.pytorch.org/whl/cpu
🏃‍♂️ Running the App

poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
✅ API Endpoints
Endpoint    Description
/api/v1/rag Query the RAG Agent
/api/v1/feedback    Submit user feedback
/metrics    Prometheus Metrics

🧪 Tests
poetry run pytest
📄 Configuration (.env)

OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=sqlite:///./test.db
LOG_LEVEL=INFO
📋 License
MIT
```
