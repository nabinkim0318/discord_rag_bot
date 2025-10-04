# ==================== Build Stage ====================
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Configure Poetry
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
RUN groupadd --gid 1000 raguser \
    && useradd --uid 1000 --gid raguser --shell /bin/bash --create-home raguser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=raguser:raguser . .

# Copy environment validation script
COPY --chown=raguser:raguser backend/scripts/validate_env.py /usr/local/bin/validate_env.py
RUN chmod +x /usr/local/bin/validate_env.py

# Switch to non-root user
USER raguser

# Health check (process check)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "sleep infinity" || exit 1

# Create startup script
RUN printf '#!/bin/bash\nset -e\necho "🔍 Validating environment variables..."\npython /usr/local/bin/validate_env.py\necho "🛠️ Starting RAG agent (development mode)..."\nexec sleep infinity' > /app/start.sh && chmod +x /app/start.sh

# Development mode - keep container alive
CMD ["/app/start.sh"]
