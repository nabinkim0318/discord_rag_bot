# Docker Deployment Guide

This project uses Docker Compose to orchestrate all services in a containerized environment.
The RAG agent is integrated as a library within the backend service rather than as a separate container.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your configuration
# Required variables:
# - DISCORD_BOT_TOKEN=your_discord_bot_token
# - OPENAI_API_KEY=your_openai_api_key
# - SECRET_KEY=your_secret_key
# - DATABASE_URL=sqlite:////app/rag_kb.sqlite3
```

### 2. Start Services

```bash
# Start all core services
docker compose up -d

# Start specific services
docker compose up -d weaviate api frontend

# Start with Discord bot
docker compose up -d bot
```

### 3. Verify Deployment

```bash
# Check service status
docker compose ps

# Check service health
curl http://localhost:8001/api/v1/health
curl http://localhost:3000  # Frontend
curl http://localhost:8080/v1/meta  # Weaviate
```

## 📋 Service Architecture

| Service      | Port | Description                    | Dependencies        |
|--------------|------|--------------------------------|-------------------|
| `weaviate`   | 8080 | Vector Database (Weaviate)     | -                 |
| `api`        | 8001 | Backend API + RAG Agent        | weaviate          |
| `bot`        | -    | Discord Bot                    | api               |
| `frontend`   | 3000 | Next.js Frontend               | api               |
| `prometheus` | 9090 | Metrics Collection             | -                 |
| `grafana`    | 3001 | Monitoring Dashboard           | prometheus        |

## 🌐 Network Configuration

### Internal Networks

- **`app_net`**: Main application network for service communication
- **`monitoring`**: Dedicated network for monitoring services

### Service Communication

Services communicate using Docker internal hostnames:

- `http://weaviate:8080` - Vector database access
- `http://api:8001` - Backend API access
- `http://prometheus:9090` - Metrics collection
- `http://grafana:3001` - Dashboard access

### External Access

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8001>
- **Weaviate**: <http://localhost:8080>
- **Prometheus**: <http://localhost:9090>
- **Grafana**: <http://localhost:3001>

## 🛠️ Management Commands

### Using Make Commands

```bash
# Build all services
make docker-build

# Start services
make docker-up

# View logs
make docker-logs
make docker-logs-api
make docker-logs-bot

# Restart services
make docker-restart

# Stop services
make docker-down

# Complete cleanup (including volumes)
make docker-clean
```

### Direct Docker Compose Commands

```bash
# Start specific services
docker compose up -d weaviate api
docker compose up -d frontend
docker compose up -d bot

# Check service status
docker compose ps

# View logs
docker compose logs -f api
docker compose logs -f bot

# Scale services (if needed)
docker compose up -d --scale api=2
```

## 🏥 Health Checks

### Automatic Health Monitoring

- **`weaviate`**: Checks `/v1/meta` endpoint every 30s
- **`api`**: Checks port 8001 connectivity every 10s
- **`bot`**: Process-based health check every 60s

### Manual Health Verification

```bash
# Check Weaviate
curl http://localhost:8080/v1/meta

# Check Backend API
curl http://localhost:8001/api/v1/health

# Check Frontend
curl http://localhost:3000

# Check Prometheus
curl http://localhost:9090/api/v1/status/config
```

## 📊 Monitoring & Observability

### Prometheus Metrics

- **URL**: <http://localhost:9090>
- **Metrics Endpoints**:
  - Backend: <http://localhost:8001/metrics>
  - Discord bot: <http://localhost:9109/metrics>
  - Weaviate: <http://localhost:8080/v1/metrics> (set `PROMETHEUS_MONITORING_ENABLED=true`)
- **Key Metrics**: RAG latency, retrieval hit rate, error rates

### Grafana Dashboards

- **URL**: <http://localhost:3001>
- **Login**: admin / admin
- **Dashboards**: RAG Bot Core Metrics Dashboard

### Log Aggregation

```bash
# View all service logs
docker compose logs

# Follow specific service logs
docker compose logs -f api
docker compose logs -f bot

# View logs with timestamps
docker compose logs -t
```

## 🔍 Troubleshooting

### Common Issues

#### Port Conflicts

```bash
# Check port usage
lsof -i :3000  # Frontend
lsof -i :8001  # Backend
lsof -i :8080  # Weaviate
lsof -i :9090  # Prometheus

# Kill processes using ports
sudo kill -9 $(lsof -t -i:8001)
```

#### Service Startup Issues

```bash
# Check service logs
docker compose logs api
docker compose logs weaviate

# Restart specific service
docker compose restart api

# Rebuild and restart
docker compose up -d --build api
```

#### Database Connection Issues

```bash
# Check database file permissions
ls -la rag_kb.sqlite3

# Reset database
rm rag_kb.sqlite3
make db-init
```

#### Memory Issues

```bash
# Check container resource usage
docker stats

# Limit memory usage
docker compose up -d --memory=2g api
```

### Volume Management

```bash
# List volumes
docker volume ls

# Remove unused volumes
docker volume prune

# Complete cleanup
make docker-clean
```

### Network Issues

```bash
# Check network connectivity
docker compose exec api ping weaviate
docker compose exec api curl http://weaviate:8080/v1/meta

# Recreate networks
docker compose down
docker network prune
docker compose up -d
```
