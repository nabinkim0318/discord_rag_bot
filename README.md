# Discord RAG Platform

A full-stack Retrieval-Augmented Generation (RAG) system with a **FastAPI backend, hybrid retrieval pipeline, Discord interface, Next.js frontend, containerized services, and observability stack**.

The project explores how to build a RAG application as an operable software system—not only a retrieval prototype—by incorporating APIs, persistence, health checks, metrics, structured logging, testing, container orchestration, and user feedback.

## Highlights

* **FastAPI backend** with REST endpoints for RAG queries, feedback, and service health
* **Hybrid retrieval architecture** combining keyword and vector retrieval with fusion and reranking
* **Weaviate vector database** for semantic retrieval
* **SQLite by default with PostgreSQL-compatible configuration** through SQLModel / SQLAlchemy
* **Docker Compose orchestration** for backend, frontend, vector store, monitoring, and Discord bot services
* **Prometheus + Grafana observability** with application and RAG-specific metrics
* Component-level **health checks** for the database, vector store, and application runtime
* **Structured request and database logging** with request IDs and latency tracking
* User **feedback collection and satisfaction metrics**
* Automated backend and RAG-agent testing through **pytest**
* **GitHub Actions CI/CD** for tests, formatting checks, Docker builds, and security-report generation
* Optional **Discord bot** and **Next.js web interface**

---

## Architecture

```mermaid
flowchart LR
    User[User] --> Web[Next.js Frontend]
    User --> Discord[Discord Bot]

    Web --> API[FastAPI Backend]
    Discord --> API

    API --> RAG[RAG Pipeline]
    API --> DB[(SQL Database)]

    RAG --> Retrieve[Hybrid Retrieval]
    Retrieve --> Vector[(Weaviate)]
    Retrieve --> Keyword[Keyword Search]
    Retrieve --> Rerank[Reranking / Fusion]

    RAG --> LLM[LLM Generation]

    API --> Metrics[Prometheus Metrics]
    Metrics --> Prometheus[Prometheus]
    Prometheus --> Grafana[Grafana]

    API --> Logs[Structured Logs]
```

### Containerized services

The local Docker environment orchestrates:

| Service      | Purpose                                |
| ------------ | -------------------------------------- |
| `api`        | FastAPI application and REST API       |
| `weaviate`   | Vector database for semantic retrieval |
| `frontend`   | Next.js user interface                 |
| `bot`        | Optional Discord interface             |
| `prometheus` | Metrics collection                     |
| `grafana`    | Monitoring dashboards                  |

The API and Weaviate services include Docker health checks, and persistent volumes are used for Weaviate, Prometheus, and Grafana data.

---

## Backend

The backend is implemented with **FastAPI, SQLModel, and SQLAlchemy**.

Core responsibilities include:

* RAG query APIs
* enhanced RAG workflows
* feedback collection
* query persistence
* database session management
* centralized error handling
* structured request logging
* Prometheus instrumentation
* dependency health endpoints

Example API groups:

```text
/api/v1/rag
/api/v1/enhanced-rag
/api/v1/feedback
/api/query
/api/v1/health
/metrics
```

FastAPI automatically exposes interactive API documentation when the backend is running:

```text
http://localhost:8001/docs
```

---

## Data Layer

The application uses SQLModel / SQLAlchemy with database behavior configured through `DATABASE_URL`.

Default local configuration:

```text
SQLite
```

The same database layer can be configured for PostgreSQL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/rag_db
```

Database sessions include:

* connection pre-ping
* connection recycling
* transaction commit / rollback handling
* structured database operation logging

This project intentionally keeps the local Docker setup lightweight; PostgreSQL is supported through configuration but is not provisioned as a default Docker Compose service.

---

## RAG Pipeline

The RAG code is separated from the application layer into a dedicated `rag_agent` package.

The retrieval system includes modules for:

* document ingestion
* indexing
* keyword retrieval
* vector retrieval
* retrieval fusion
* reranking
* query processing
* generation
* evaluation

```text
rag_agent/
├── ingestion/
├── indexing/
├── retrieval/
├── query/
├── generation/
├── evaluation/
└── core/
```

Retrieval behavior can be configured through environment variables such as:

```bash
DEFAULT_TOP_K=5
MAX_TOP_K=20

BM25_WEIGHT=0.4
VECTOR_WEIGHT=0.6
MMR_LAMBDA=0.65
```

The vector layer uses **Weaviate**, with configurable embedding and LLM providers.

---

## Observability

Observability is a first-class part of the project rather than an afterthought.

### Prometheus metrics

The FastAPI service exposes Prometheus-compatible metrics at:

```text
/metrics
```

The application records metrics including:

* RAG request counts
* RAG failures
* RAG query latency
* end-to-end pipeline latency
* retrieval hit outcomes
* requested retrieval depth (`top_k`)
* feedback submissions
* user satisfaction
* health-check outcomes
* database health latency
* vector-store health latency
* circuit-breaker state

Examples:

```text
rag_requests_total
rag_failures_total
rag_pipeline_latency_seconds
rag_retrieval_hits_total
feedback_submissions_total
feedback_satisfaction_rate
health_check_db_total
health_check_vector_store_total
```

### Grafana

Grafana runs as part of the Docker Compose environment and uses Prometheus as its metrics source.

Local services:

```text
Prometheus: http://localhost:9090
Grafana:    http://localhost:3001
```

The repository includes Grafana provisioning and dashboard configuration under:

```text
ops/grafana/
```

---

## Health Checks

The API exposes service-level health endpoints:

```text
GET /api/v1/health/
GET /api/v1/health/check
GET /api/v1/health/db
GET /api/v1/health/llm
GET /api/v1/health/vector-store
```

Implemented checks include:

### Application

Validates basic application runtime behavior, including writable filesystem access.

### Database

Executes a real database ping:

```sql
SELECT 1
```

and records latency and failure metrics.

### Vector Store

Checks the availability and health of the configured Weaviate service.

### LLM

The LLM health endpoint and metrics interface are implemented, but the external LLM API call is currently disabled in the health check to keep local and CI environments deterministic.

---

## Logging & Error Handling

Backend requests receive generated request IDs and structured logging context.

Request logging captures information such as:

* HTTP method
* endpoint
* response status
* request duration
* request ID
* available user / channel context

Database operations also record session lifecycle events such as:

```text
SESSION_START
SESSION_COMMIT
SESSION_ROLLBACK
SESSION_CLOSE
```

The FastAPI application uses centralized exception handling so API failures can be processed consistently.

---

## Feedback Loop

The platform includes feedback APIs and metrics rather than treating generation as a one-way interaction.

Feedback infrastructure supports:

* user feedback submission
* feedback persistence
* positive / negative response tracking
* feedback history and summaries
* user satisfaction metrics

This allows retrieval and generation behavior to be evaluated with signals from actual usage.

---

## CI/CD and Code Quality

GitHub Actions runs automated checks for the backend, RAG agent, frontend, and Docker images.

The workflow includes:

### Backend

* Python 3.11 setup
* Poetry dependency installation
* isort
* Ruff linting / formatting checks
* pytest

### RAG Agent

* Poetry dependency installation
* linting / formatting checks
* pytest

### Frontend

* Node.js setup
* dependency installation
* Prettier checks
* frontend test command

### Containers

CI builds Docker images for:

* backend
* RAG agent
* frontend
* Discord bot

Docker Buildx caching is enabled to improve build efficiency.

### Security

The pipeline also generates a **Bandit static-analysis report** for the Python backend and uploads it as a CI artifact.

The security scan is currently informational rather than a blocking CI gate.

---

## Quick Start

### Requirements

* Docker
* Docker Compose
* Git
* OpenAI API key or compatible configured provider

Clone the repository:

```bash
git clone https://github.com/nabinkim0318/discord_rag_bot.git
cd discord_rag_bot
```

Create the environment file:

```bash
cp env.template .env
```

At minimum, configure:

```bash
OPENAI_API_KEY=your_key
SECRET_KEY=your_secret_key
```

Optional Discord integration also requires:

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token
```

Validate the environment:

```bash
make env-check
```

---

## Run with Docker

Build the containers:

```bash
make docker-build
```

Start the core services:

```bash
make docker-up
```

This starts the API, frontend, Weaviate, Prometheus, and Grafana services.

To also start the Discord bot:

```bash
make docker-up-with-bot
```

View logs:

```bash
make docker-logs
```

Backend-only logs:

```bash
make docker-logs-api
```

Stop the environment:

```bash
make docker-down
```

---

## Local Development

Install project dependencies:

```bash
make install
```

Run the backend:

```bash
make run-backend
```

Run the frontend:

```bash
make run-frontend
```

Run the RAG agent from the CLI:

```bash
make run-rag
```

---

## Testing

Run the complete project test commands:

```bash
make test
```

Or run components individually:

```bash
make test-backend
make test-rag
make test-frontend
```

Backend and RAG tests use `pytest`.

The frontend test workflow uses Jest.

---

## Code Quality

Run lint checks:

```bash
make lint
```

Run formatting:

```bash
make format
```

Verify formatting without modifying files:

```bash
make format-check
```

Run pre-commit checks:

```bash
make precommit
```

---

## RAG Evaluation

The repository includes a separate evaluation workflow for comparing retrieval / generation configurations and prompt versions.

Example:

```bash
make eval-rag
```

Multiple prompt versions can be evaluated with:

```bash
make eval-rag-all
```

This separation keeps application behavior and RAG evaluation reproducible rather than embedding experimentation directly into API code.

---

## Project Structure

```text
discord_rag_bot/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # config, logging, metrics, errors
│   │   ├── db/              # database sessions
│   │   ├── models/          # SQLModel data models
│   │   └── services/        # application services
│   └── tests/
│
├── rag_agent/
│   ├── ingestion/           # document ingestion
│   ├── indexing/            # indexing workflows
│   ├── retrieval/           # keyword/vector retrieval & reranking
│   ├── generation/          # generation pipeline
│   ├── evaluation/          # RAG evaluation
│   └── tests/
│
├── frontend/                # Next.js frontend
├── bots/                    # Discord bot
│
├── ops/
│   ├── prometheus/
│   └── grafana/
│
├── scripts/
├── docs/
├── docker-compose.yaml
├── env.template
├── Makefile
└── .github/workflows/
```

---

## Engineering Focus

This project was built to explore the engineering work required around an AI system—not only model invocation.

Areas of focus include:

* separating application and RAG concerns
* exposing reusable APIs
* containerizing multiple dependent services
* designing observable application behavior
* monitoring retrieval and generation performance
* implementing dependency-specific health checks
* persisting queries and feedback
* building reproducible evaluation workflows
* incorporating automated tests and CI
* documenting operational and troubleshooting workflows

---

## Current Limitations

This repository is a development and engineering portfolio project rather than a fully managed production deployment.

Notable limitations include:

* the default Docker environment uses SQLite rather than provisioning PostgreSQL
* local Docker configuration contains development-oriented defaults that should be replaced before production deployment
* the LLM health endpoint does not currently perform an external provider request
* CI security scanning generates reports but does not currently block merges
* production secrets, TLS termination, managed database infrastructure, and cloud orchestration are outside the current repository scope

These boundaries are documented intentionally so implemented behavior is distinguishable from planned production infrastructure.

---

## Documentation

Additional technical documentation is available under:

```text
docs/
```

including guides for:

* Docker setup
* observability
* RAG architecture
* testing
* contribution workflows

---

## License

MIT License.
