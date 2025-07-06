# ======== Project Setup ========

.PHONY: install setup clean lint format test run-backend run-rag lock update check precommit commit

# ==== Install Dependencies ====
install:
	poetry install
	pre-commit install

setup:
	poetry shell

# ======== Development ========

lint:
	poetry run black --check .
	poetry run isort --check .
	poetry run flake8 .

format:
	poetry run black .
	poetry run isort .

test:
	poetry run pytest tests

# ======== App Run (Backend & RAG Agent CLI) ========

run-backend:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-rag:
	poetry run python rag_agent/generation/cli_generate.py --query "Sample Query"

# ======== Maintenance ========

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

lock:
	poetry lock

update:
	poetry update

check:
	poetry check

precommit:
	poetry run pre-commit run --all-files

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
