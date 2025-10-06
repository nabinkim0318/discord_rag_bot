# 🔗 Discord RAG Bot - Backend API

This is the FastAPI-based backend service for the Discord RAG Bot project.
It handles API endpoints for querying the RAG agent, receiving user feedback, logging, and metrics collection.

## 📂 Project Structure

```text
backend/
├── app/                    # Main FastAPI application
│   ├── api/               # API routes (v1)
│   │   ├── v1/           # Versioned API endpoints
│   │   └── query.py      # Legacy query endpoint
│   ├── core/             # Core utilities
│   │   ├── config.py     # Settings and configuration
│   │   ├── logging.py    # Structured logging setup
│   │   └── metrics.py    # Prometheus metrics
│   ├── db/               # Database configuration
│   ├── models/           # Pydantic data models
│   ├── services/         # Business logic
│   │   ├── rag_service.py           # RAG pipeline service
│   │   ├── enhanced_rag_service.py  # Enhanced RAG service
│   │   └── feedback_service.py      # Feedback collection
│   └── utils/            # Utility functions
├── tests/                # Test suite
├── Dockerfile            # Container configuration
├── pyproject.toml        # Poetry project configuration
├── requirements.txt      # Pip dependencies
└── README.md            # This documentation
```text

## 🚀 Features

### Core Functionality

- **REST API**: Query the RAG pipeline via HTTP endpoints
- **Feedback Collection**: User satisfaction tracking with 👍👎 reactions
- **Metrics Tracking**: Prometheus metrics for performance monitoring
- **Health Checks**: Database, LLM, and vector store monitoring
- **Error Handling**: Graceful fallback mechanisms

### Technical Features

- **FastAPI**: Modern, fast web framework with automatic OpenAPI docs
- **SQLAlchemy**: Database ORM with SQLite/PostgreSQL support
- **Pydantic**: Data validation and settings management
- **Structured Logging**: JSON-formatted logs with Loguru
- **Environment Configuration**: Flexible `.env`-based configuration

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- Docker (for containerized deployment)

### Local Development

```textbash
# Install dependencies with Poetry
poetry install --with dev

# Activate virtual environment
poetry shell

# If torch installation fails, install separately:
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run the development server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```text

### Docker Deployment

```textbash
# Build and run with Docker Compose
docker compose up -d api

# Or build the backend container directly
docker build -t discord-rag-backend .
docker run -p 8001:8001 --env-file .env discord-rag-backend
```text

## 📡 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag` | POST | Query the RAG pipeline |
| `/api/v1/feedback` | POST | Submit user feedback |
| `/api/query/` | POST | Legacy query endpoint |
| `/api/v1/health` | GET | Health check endpoint |
| `/metrics` | GET | Prometheus metrics |

### Example Usage

```textbash
# Query the RAG system
curl -X POST "http://localhost:8001/api/v1/rag" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the demo day schedule?", "top_k": 5}'

# Submit feedback
curl -X POST "http://localhost:8001/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -d '{"query_id": "123", "rating": "positive", "user_id": "user456"}'
```text

## 🧪 Testing

```textbash
# Run all tests
poetry run pytest

# Run specific test files
poetry run pytest tests/test_rag.py
poetry run pytest tests/test_feedback_integration.py

# Run with coverage
poetry run pytest --cov=app tests/
```text

## 📄 Configuration

### Environment Variables (.env)

```textbash
# ==================== Backend API Configuration ====================
BACKEND_BASE=http://api:8001
API_TIMEOUT=30
HOST=0.0.0.0
PORT=8001
DEBUG=false

# ==================== Database Configuration ====================
DATABASE_URL=sqlite:////app/rag_kb.sqlite3

# ==================== LLM Configuration ====================
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini

# ==================== Vector Database (Weaviate) ====================
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=
WEAVIATE_CLASS_NAME=KBChunk

# ==================== Logging Configuration ====================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=logs

# ==================== CORS Configuration ====================
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_ALLOW_CREDENTIALS=true
```text

## 📊 Monitoring & Observability

### Prometheus Metrics

The backend exposes metrics at `/metrics` endpoint:

- **RAG Pipeline Latency**: Response time distribution
- **Retrieval Hit Rate**: Search success rate
- **RAG Failure Rate**: Error rate tracking
- **Request Volume**: API usage by endpoint
- **Feedback Analytics**: User satisfaction metrics

### Health Checks

- **Database Health**: Connection and query performance
- **LLM Health**: OpenAI API connectivity
- **Vector Store Health**: Weaviate connectivity
- **Overall System Health**: Aggregated health status

## 🔧 Development

### Code Quality

```textbash
# Format code
black .
isort .

# Lint code
ruff check .
flake8

# Type checking
mypy app/
```text

### Pre-commit Hooks

```textbash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```text

## 📋 License

MIT License - see LICENSE file for details.
