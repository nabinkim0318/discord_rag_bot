# ======== Project Setup ========

.PHONY: install-backend install-rag install-frontend backend-setup rag-setup frontend-setup clean lint-backend lint-rag lint-frontend format-backend format-rag format-frontend test-backend test-rag test-frontend run-backend run-rag run-frontend lock-backend lock-rag update-backend update-rag update-frontend check-backend check-rag check-frontend precommit-backend precommit-rag precommit-frontend commit env-check env-init db-init

# ==== Install Dependencies ====
install: install-backend install-rag install-frontend

install-backend:
	cd backend && poetry install || true
	cd backend && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

install-rag:
	cd rag_agent && poetry install || true
	cd rag_agent && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

install-frontend:
	cd frontend && npm install

setup: backend-setup rag-setup frontend-setup

backend-setup:
	cd backend && poetry shell

rag-setup:
	cd rag_agent && poetry shell

frontend-setup:
	cd frontend && npm install

# ======== Environment & Database ========

env-check:
	@echo "🔍 Checking environment variables..."
	python scripts/check_env.py

env-init:
	@echo "📝 Initializing environment..."
	@if [ ! -f .env ]; then \
		echo "📋 Copying env.template to .env..."; \
		cp env.template .env; \
		echo "✅ Created .env file from template"; \
		echo "⚠️  Please edit .env file with your actual values"; \
	else \
		echo "✅ .env file already exists"; \
	fi

db-init:
	@echo "🗄️  Initializing database..."
	python scripts/init_db.py

db-init-alembic:
	@echo "🗄️  Initializing database with Alembic..."
	INIT_ALEMBIC=true python scripts/init_db.py

# ======== Development ========
lint: lint-backend lint-rag lint-frontend

lint-backend:
	cd backend && poetry run isort --check --profile black .
	cd backend && poetry run ruff check --line-length 88 .

lint-rag:
	cd rag_agent && poetry run isort --check --profile black .
	cd rag_agent && poetry run ruff check --line-length 88 .

lint-frontend:
	cd frontend && npm run format:check

format: format-backend format-rag format-frontend format-all

# 🎯 최적의 포맷팅 도구 조합 (자동화) - Ruff 전용
format-backend:
	@echo "🎨 포맷팅 Backend 코드..."
	cd backend && poetry run isort --profile black --line-length 88 .
	cd backend && poetry run ruff check --fix --line-length 88 .
	cd backend && poetry run ruff format .

format-rag:
	@echo "🎨 포맷팅 RAG Agent 코드..."
	cd rag_agent && poetry run isort --profile black --line-length 88 .
	cd rag_agent && poetry run ruff check --fix --line-length 88 .
	cd rag_agent && poetry run ruff format .

# 🎯 고급 포맷팅 (yapf 포함) - 느릴 수 있음
format-backend-advanced:
	@echo "🎨 고급 포맷팅 Backend 코드..."
	cd backend && poetry run isort --profile black --line-length 88 .
	cd backend && poetry run black --line-length 88 .
	cd backend && poetry run yapf --in-place --recursive --style='{based_on_style: pep8, column_limit: 88}' .
	cd backend && poetry run ruff check --fix --line-length 88 .

format-rag-advanced:
	@echo "🎨 고급 포맷팅 RAG Agent 코드..."
	cd rag_agent && poetry run isort --profile black --line-length 88 .
	cd rag_agent && poetry run black --line-length 88 .
	cd rag_agent && poetry run yapf --in-place --recursive --style='{based_on_style: pep8, column_limit: 88}' .
	cd rag_agent && poetry run ruff check --fix --line-length 88 .

format-frontend:
	@echo "🎨 포맷팅 Frontend 코드..."
	cd frontend && npm run format

format-all:
	@echo "🎨 전체 프로젝트 포맷팅..."
	npx prettier --write .
	$(MAKE) format-backend
	$(MAKE) format-rag

# 🔍 포맷팅 검사 (CI/CD용)
format-check: format-check-backend format-check-rag format-check-frontend

format-check-backend:
	@echo "🔍 Backend 포맷팅 검사..."
	cd backend && poetry run isort --check-only --profile black --line-length 88 .
	cd backend && poetry run ruff check --line-length 88 .
	cd backend && poetry run ruff format --check .

format-check-rag:
	@echo "🔍 RAG Agent 포맷팅 검사..."
	cd rag_agent && poetry run isort --check-only --profile black --line-length 88 .
	cd rag_agent && poetry run ruff check --line-length 88 .
	cd rag_agent && poetry run ruff format --check .

format-check-frontend:
	@echo "🔍 Frontend 포맷팅 검사..."
	cd frontend && npm run format:check

test: test-backend test-rag test-frontend

test-backend:
	cd backend && poetry run pytest tests

test-backend-error:
	cd backend && poetry run pytest tests/test_error_handling.py -v

test-rag:
	cd rag_agent && poetry run pytest tests

test-frontend:
	cd frontend && npm test

# ======== App Run (Backend & RAG Agent CLI) ========

run-backend:
	cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-rag:
	cd rag_agent && poetry run python rag_agent/generation/cli_generate.py --query "Sample Query"

run-frontend:
	cd frontend && npm run dev

# ======== RAG Evaluation ========

eval-rag:
	cd rag_agent && poetry run python evaluation/cli_eval.py --input data/test_dataset.json --prompt-version v1.1

eval-rag-all:
	cd rag_agent && poetry run python evaluation/cli_eval.py --input data/test_dataset.json --prompt-version v1.0
	cd rag_agent && poetry run python evaluation/cli_eval.py --input data/test_dataset.json --prompt-version v1.1
	cd rag_agent && poetry run python evaluation/cli_eval.py --input data/test_dataset.json --prompt-version v2.0

# ======== Maintenance ========

clean-backend:
	cd backend && poetry run find . -type d -name "__pycache__" -exec rm -r {} +
	cd backend && rm -rf .pytest_cache .ruff_cache .mypy_cache

clean-rag:
	cd rag_agent && poetry run find . -type d -name "__pycache__" -exec rm -r {} +
	cd rag_agent && rm -rf .pytest_cache .ruff_cache .mypy_cache

clean: clean-backend clean-rag
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

lock: lock-backend lock-rag

lock-backend:
	cd backend && poetry lock

lock-rag:
	cd rag_agent && poetry lock

update: update-backend update-rag

update-backend:
	cd backend && poetry update

update-rag:
	cd rag_agent && poetry update

check: check-backend check-rag

check-backend:
	cd backend && poetry check

check-rag:
	cd rag_agent && poetry check

precommit: precommit-backend precommit-rag

precommit-backend:
	cd backend && poetry run pre-commit run --all-files

precommit-rag:
	cd rag_agent && poetry run pre-commit run --all-files

# ======== Docker Commands ========

docker-up:
	docker compose up -d

docker-up-with-bot:
	docker compose --profile discord up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

docker-logs-api:
	docker compose logs -f api

docker-logs-bot:
	docker compose logs -f bot

docker-restart:
	docker compose restart

docker-clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# ======== Git Shortcuts ========

commit:
ifndef m
	$(error ❌ Please provide a commit message like: make commit m="your message")
endif
	@git status
	@git add .
	@git commit -m "$(m)"
	@git push
	@git status
