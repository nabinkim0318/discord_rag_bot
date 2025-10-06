# ==================== Build Stage ====================
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY discord/requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

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
RUN groupadd --gid 1000 botuser \
    && useradd --uid 1000 --gid botuser --shell /bin/bash --create-home botuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=botuser:botuser . .

# Copy environment validation script (create a simple one if not available)
RUN printf '#!/usr/bin/env python3\nimport os\nimport sys\n\nrequired_vars = ["DISCORD_BOT_TOKEN"]\nmissing = []\nfor var in required_vars:\n    if not os.getenv(var):\n        missing.append(var)\n\nif missing:\n    print(f"❌ Missing environment variables: {missing}")\n    sys.exit(1)\nelse:\n    print("✅ Environment variables validated")\n' > /usr/local/bin/validate_env.py && chmod +x /usr/local/bin/validate_env.py

# Create startup script as root before switching user
RUN printf '#!/bin/bash\nset -e\necho "🔍 Validating environment variables..."\npython /usr/local/bin/validate_env.py\necho "🤖 Starting Discord bot..."\nexec python discord/bot.py' > /app/start.sh && chmod +x /app/start.sh && chown botuser:botuser /app/start.sh

# Switch to non-root user
USER botuser

# Health check (simple process check)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*discord/bot.py" || exit 1

# Start application
CMD ["/app/start.sh"]
