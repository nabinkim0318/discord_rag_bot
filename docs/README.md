# Discord RAG Bot

## Documentation Index

- Getting Started: `DOCKER.md`
- System Guide: `RAG_SYSTEM_GUIDE.md`
- Contributing: `CONTRIBUTING.md`
- Observability: `observability.md`
- Test Structure: `TEST_STRUCTURE.md`
- Ops configs: `../ops/` (Prometheus, Grafana, Compose)

## Roles & Responsibilities

- Discord Bot: Slash commands, feedback buttons, regenerate
- Backend API: `/api/query/`, `/api/v1/feedback`, health endpoints
- RAG Engine: Hybrid retrieval (BM25+Vector), Cross-Encoder rerank, MMR, context packing
- Monitoring: Prometheus metrics, Grafana dashboards

A comprehensive RAG system with Discord bot integration, enhanced monitoring, and feedback collection.

## 🚀 Features

### Core RAG Pipeline

- **Hybrid Search**: Combines BM25 and vector search for optimal retrieval
- **Enhanced RAG**: Advanced query processing with intent detection
- **Multi-route Search**: Supports different search strategies
- **Context Packing**: Intelligent token budget management
- **Response Generation**: Discord-optimized output formatting

### Monitoring & Observability

- **Prometheus Metrics**: Comprehensive performance monitoring
- **Grafana Dashboards**: Real-time visualization of key metrics
- **Health Checks**: Database, LLM, and vector store monitoring
- **Feedback Analytics**: User satisfaction tracking

### Discord Integration

- **Slash Commands**: `/ask`, `/feedback` commands
- **Reaction Feedback**: 👍👎 emoji-based feedback collection
- **User Context**: Channel and user ID tracking
- **Error Handling**: Graceful fallback mechanisms

## 📊 Monitoring Dashboard

### Key Metrics Tracked

- **RAG Pipeline Latency**: p95/p50 response times
- **Retrieval Hit Rate**: Search success rate (target: >95%)
- **RAG Failure Rate**: Error rate (target: <5%)
- **User Satisfaction**: Feedback-based satisfaction rate (target: >80%)
- **Request Volume**: API usage by endpoint
- **Feedback Analytics**: Up/down vote distribution

### Grafana Dashboard

Access the monitoring dashboard at: <http://localhost:3001>

- **Login**: admin / admin
- **Dashboard**: RAG Bot > RAG Bot Core Metrics Dashboard

## 🛠️ Architecture

### Backend Services

- **FastAPI**: REST API with automatic documentation
- **SQLAlchemy**: Database ORM with SQLite/PostgreSQL support
- **Prometheus**: Metrics collection and export
- **Weaviate**: Vector database for embeddings

### Backend API (Details)

This project includes a FastAPI-based backend service that handles RAG queries, feedback, logging, and metrics.

Key features:

- REST API endpoints for RAG queries and feedback submission
- Prometheus metrics and health checks (DB/LLM/Vector store)
- Structured logging and error handling

Quickstart (local):

```bash
cd backend
poetry install --with dev
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Docker:

```bash
docker compose up -d api
# or
docker build -t discord-rag-backend backend/
docker run -p 8001:8001 --env-file .env discord-rag-backend
```

Core endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag` | POST | Query the RAG pipeline |
| `/api/v1/feedback/submit` | POST | Submit user feedback |
| `/api/query/` | POST | Query with database storage |
| `/api/v1/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### RAG Components

- **Document Ingestion**: PDF, text file processing
- **Chunking**: Intelligent document segmentation
- **Embeddings**: OpenAI/SentenceTransformers support
- **Retrieval**: Hybrid BM25 + vector search
- **Generation**: LLM response generation with context

### Discord Bot

- **Discord.py**: Bot framework with slash commands
- **Async Processing**: Non-blocking request handling
- **Feedback Collection**: User satisfaction tracking
- **Error Recovery**: Graceful degradation

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key (for embeddings and LLM)
- Discord Bot Token (for Discord integration)

### Environment Setup

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your configuration
# Required variables:
# - DISCORD_BOT_TOKEN=your_discord_bot_token
# - OPENAI_API_KEY=your_openai_api_key
# - SECRET_KEY=your_secret_key
# - DATABASE_URL=sqlite:////app/rag_kb.sqlite3

# Check environment variables
make env-check

# Initialize database (optional - will be created automatically)
make db-init
```

### Docker Deployment

```bash
# Start all core services
docker compose up -d

# Start with Discord bot (requires DISCORD_BOT_TOKEN)
docker compose up -d bot

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Access services
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8001
# - Weaviate: http://localhost:8080
# - Grafana: http://localhost:3001 (admin/admin)
```

### Service URLs

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8001>
- **API Documentation**: <http://localhost:8001/docs>
- **Weaviate**: <http://localhost:8080>
- **Prometheus**: <http://localhost:9090>
- **Grafana**: <http://localhost:3001> (admin/admin)

## 📈 Monitoring & Metrics

### Prometheus Metrics

Access metrics at: <http://localhost:8001/metrics>

**Key Metrics:**

- `rag_pipeline_latency_seconds`: End-to-end pipeline latency
- `rag_retrieval_hits_total`: Search success/failure counts
- `rag_requests_total`: API request volume
- `feedback_submissions_total`: User feedback counts
- `rag_failures_total`: Error tracking

### Grafana Dashboards

**RAG Bot Core Metrics Dashboard** includes:

- Pipeline latency trends (p95/p50)
- Retrieval hit rate monitoring
- Failure rate alerts
- User satisfaction tracking
- Request volume analysis
- Feedback analytics

### Health Checks

- **Database**: `/api/v1/health/db`
- **LLM**: `/api/v1/health/llm`
- **Vector Store**: `/api/v1/health/vector-store`
- **Overall**: `/api/v1/health/`

## 🤖 Discord Bot Usage

### Slash Commands

```bash
/ask <question> - Ask a question to the RAG system
/feedback [days] - View feedback statistics
```

### Feedback Collection

- **Reaction Feedback**: Click 👍 or 👎 on bot responses
- **Text Feedback**: Use `/feedback` command for detailed feedback
- **Automatic Tracking**: User satisfaction metrics

## 🔧 Development

### Local Development

```bash
# Install dependencies
pip install -r backend/requirements.txt
pip install -r rag_agent/requirements.txt

# Run backend
cd backend && python -m uvicorn app.main:app --reload

# Run Discord bot
cd bots && python run_bot.py
```

### Testing

```bash
# Run tests
pytest backend/tests/

# Test feedback service
python scripts/test_feedback.py

# Test RAG pipeline
python scripts/smoke_retrieval.py

# Check environment variables
make env-check
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## 📁 Project Structure

```text
discord_rag_bot/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core utilities
│   │   ├── db/             # Database models
│   │   ├── services/       # Business logic
│   │   └── models/         # Data models
│   └── tests/             # Test suite
├── bots/                   # Discord bot
│   └── discord/           # Bot implementation
├── rag_agent/             # RAG pipeline
│   ├── generation/        # Response generation
│   ├── retrieval/         # Search components
│   ├── indexing/          # Document processing
│   └── evaluation/        # Performance testing
├── monitoring/            # Observability
│   ├── grafana/           # Dashboard configs
│   └── prometheus.yml     # Metrics config
└── scripts/               # Utility scripts
```

## 🔍 API Endpoints

### RAG Endpoints

- `POST /api/v1/rag/` - Standard RAG query
- `POST /api/v1/enhanced-rag/` - Enhanced RAG with advanced features
- `POST /api/query/` - Query with database storage

### Feedback Endpoints

- `POST /api/v1/feedback/submit` - Submit user feedback
- `GET /api/v1/feedback/stats/{query_id}` - Get feedback statistics
- `GET /api/v1/feedback/history/{user_id}` - User feedback history
- `GET /api/v1/feedback/summary` - Overall feedback summary

### Health Endpoints

- `GET /api/v1/health/` - Overall health check
- `GET /api/v1/health/db` - Database health
- `GET /api/v1/health/llm` - LLM service health
- `GET /api/v1/health/vector-store` - Vector store health

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection**: Check `DATABASE_URL` in `.env`
2. **Weaviate Connection**: Verify `WEAVIATE_URL` and API key
3. **Discord Bot**: Ensure `DISCORD_BOT_TOKEN` is valid
4. **Metrics**: Check Prometheus configuration

### Logs

```bash
# View all logs
docker compose logs -f

# Specific service logs
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f grafana
```

### Performance Tuning

- **Retrieval**: Adjust `top_k` parameters
- **Generation**: Configure token budgets
- **Database**: Optimize connection pooling
- **Monitoring**: Set appropriate alert thresholds

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:

- Check the troubleshooting section
- Review the API documentation
- Examine the monitoring dashboards
- Check service logs for errors
