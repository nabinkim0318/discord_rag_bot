FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

COPY . .

CMD ["sleep", "infinity"]
