# ======== Project Setup ========

.PHONY: install-backend install-rag backend-setup rag-setup clean lint-backend lint-rag format-backend format-rag test-backend test-rag run-backend run-rag lock-backend lock-rag update-backend update-rag check-backend check-rag precommit-backend precommit-rag commit

# ==== Install Dependencies ====
install: install-backend install-rag

install-backend:
	cd backend && poetry install || true
	cd backend && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

install-rag:
	cd rag_agent && poetry install || true
	cd rag_agent && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

setup: backend-setup rag-setup

backend-setup:
	cd backend && poetry shell

rag-setup:
	cd rag_agent && poetry shell

# ======== Development ========
lint: lint-backend lint-rag

lint-backend:
	cd backend && poetry run black --check .
	cd backend && poetry run isort --check .
	cd backend && poetry run flake8 .

lint-rag:
	cd rag_agent && poetry run black --check .
	cd rag_agent && poetry run isort --check .
	cd rag_agent && poetry run flake8 .

format: format-backend format-rag

format-backend:
	cd backend && poetry run isort .
	cd backend && poetry run black .

format-rag:
	cd rag_agent && poetry run isort .
	cd rag_agent && poetry run black .

test: test-backend test-rag

test-backend:
	cd backend && poetry run pytest tests

test-rag:
	cd rag_agent && poetry run pytest tests

# ======== App Run (Backend & RAG Agent CLI) ========

run-backend:
	cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-rag:
	cd rag_agent && poetry run python rag_agent/generation/cli_generate.py --query "Sample Query"

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
