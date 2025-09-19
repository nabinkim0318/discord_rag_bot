# Docker Compose Settings

This project manages all services in a single Docker Compose file.

## 🚀 Quick Start

### 1. Environment Variable Settings

```bash
# Backend environment variables
cp backend/.env.example backend/.env
# Set your OPENAI_API_KEY

# Discord bot environment variables (optional)
cp bots/env.template bots/.env
# Set your DISCORD_TOKEN
```

### 2. Start Services

```bash
# Start basic services only (excluding Discord bot)
make docker-up

# Start all services including Discord bot
make docker-up-with-bot
```

## 📋 Service Configuration

| Service      | Port | Description          | Dependencies        |
| ------------ | ---- | -------------------- | ------------------- |
| `weaviate`   | 8080 | Vector Database      | -                   |
| `api`        | 8001 | Backend API          | weaviate, rag_agent |
| `rag_agent`  | -    | RAG Agent            | -                   |
| `bot`        | -    | Discord Bot          | api                 |
| `frontend`   | 3000 | Next.js Frontend     | api                 |
| `prometheus` | 9090 | Metrics Collection   | -                   |
| `grafana`    | 3001 | Monitoring Dashboard | prometheus          |

## 🌐 Network Configuration

- **`app_net`**: Main application network
- **`monitoring`**: Monitoring services network

Service-to-service communication uses hostnames:

- `http://weaviate:8080` - Access Weaviate
- `http://api:8001` - Access Backend API

## 🛠️ Useful Commands

```bash
# Build services
make docker-build

# Check logs
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

## 🔧 Profile Usage

The Discord bot is configured as an optional profile:

```bash
# Start without Discord bot
docker compose up -d

# Start including Discord bot
docker compose --profile discord up -d
```

## 🏥 Health Checks

The following services include health checks:

- `weaviate`: Checks `/v1/meta` endpoint
- `api`: Checks `/health` endpoint

## 📊 Monitoring

- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3001](http://localhost:3001) (admin/admin123)

## 🔍 Troubleshooting

### Port Conflicts

```bash
# Check which ports are in use
lsof -i :3000
lsof -i :8001
lsof -i :8080
```

### Volume Management

```bash
# Remove all volumes
make docker-clean
```

### Log Checking

```bash
# Check specific service logs
docker compose logs -f api
docker compose logs -f weaviate
```
