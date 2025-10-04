# ==================== Build Stage ====================
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Configure Poetry for global installation
RUN poetry config virtualenvs.create false \
    && poetry config installer.parallel false

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (production only)
RUN poetry install --only=main --no-interaction --no-ansi --no-root

# ==================== Runtime Stage ====================
FROM python:3.11-slim as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.local/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Copy environment validation scripts and startup script
COPY --chown=appuser:appuser scripts/validate_env.py /usr/local/bin/validate_env.py
COPY --chown=appuser:appuser scripts/validate_env_skip.py /usr/local/bin/validate_env_skip.py
COPY --chown=appuser:appuser scripts/start.sh /app/start.sh
RUN chmod +x /usr/local/bin/validate_env.py /usr/local/bin/validate_env_skip.py /app/start.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health/ || exit 1

# Expose port
EXPOSE 8001

# Start application
CMD ["/app/start.sh"]
