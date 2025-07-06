# ======== Project Setup ========

.PHONY: install-backend install-rag setup-backend setup-rag clean lint-backend lint-rag format-backend format-rag test-backend test-rag run-backend run-rag lock-backend lock-rag update-backend update-rag check-backend check-rag precommit-backend precommit-rag commit

# ==== Install Dependencies ====
install: install-backend install-rag

install-backend:
	cd backend && poetry install || true
	cd backend && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

install-rag:
	cd rag_agent && poetry install || true
	cd rag_agent && poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

setup: setup-backend setup-rag

setup-backend:
	cd backend && poetry shell

setup-rag:
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
	cd backend && poetry run black .
	cd backend && poetry run isort .

format-rag:
	cd rag_agent && poetry run black .
	cd rag_agent && poetry run isort .

test: test-backend test-rag

test-backend:
	cd backend && poetry run pytest tests

test-rag:
	cd rag_agent && poetry run pytest tests

# ======== App Run (Backend & RAG Agent CLI) ========

run-backend:
	cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-rag:
	cd rag_agent && poetry run python rag_agent/generation/cli_generate.py --query "Sample Query"

# ======== Maintenance ========

clean:
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
