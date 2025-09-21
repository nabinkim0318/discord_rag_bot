FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

# 빌드에 필요한 툴만 최소 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Poetry 설치 + 전역 설치 모드
RUN pip install --no-cache-dir poetry==${POETRY_VERSION} \
 && poetry config virtualenvs.create false

# 2) 의존성만 먼저 설치 (소스 없이도 가능하도록 --no-root)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-interaction --no-ansi

# 3) 이제 소스를 복사 (여기서야 현재 프로젝트가 생김)
COPY . .

# 4) 바로 실행 (전역 경로에 uvicorn 깔렸음)
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8001"]
