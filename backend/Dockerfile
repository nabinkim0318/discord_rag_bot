FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

# Install minimal tools needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Install Poetry + global installation mode
RUN pip install --no-cache-dir poetry==${POETRY_VERSION} \
 && poetry config virtualenvs.create false

# 2) Install dependencies first (--no-root to work without source)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-interaction --no-ansi

# 3) Now copy source (current project is created here)
COPY . .

# 4) Run directly (uvicorn installed in global path)
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8001"]
