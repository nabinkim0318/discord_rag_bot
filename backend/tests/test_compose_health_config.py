"""Static checks for Compose/Docker health and local-dev security defaults."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yaml"
DOCKERFILE_PATH = REPO_ROOT / "backend" / "Dockerfile"
STALE_COMPOSE = "ops/compose/docker-compose.yaml"


def _compose_text() -> str:
    return COMPOSE_PATH.read_text()


def _dockerfile_text() -> str:
    return DOCKERFILE_PATH.read_text()


def test_stale_duplicate_compose_is_removed_and_unreferenced():
    assert not (REPO_ROOT / STALE_COMPOSE).exists()
    skip_suffixes = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".sqlite3"}
    skip_parts = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
    matches = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix in skip_suffixes:
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if STALE_COMPOSE in text:
            matches.append(str(path.relative_to(REPO_ROOT)))
    assert matches == []


def test_root_compose_does_not_use_tcp_socket_open_as_api_readiness():
    compose = _compose_text()
    assert "socket.create_connection" not in compose
    assert "/api/v1/health/livez" in compose


def test_docker_and_compose_healthchecks_target_existing_livez():
    compose = _compose_text()
    dockerfile = _dockerfile_text()
    assert "http://127.0.0.1:8001/api/v1/health/livez" in compose
    assert "http://localhost:8001/api/v1/health/livez" in dockerfile


def test_host_bindings_are_loopback_for_published_services():
    compose = _compose_text()
    for binding in (
        "127.0.0.1:8080:8080",
        "127.0.0.1:8001:8001",
        "127.0.0.1:3000:3000",
        "127.0.0.1:9090:9090",
        "127.0.0.1:3001:3000",
    ):
        assert binding in compose
    assert '- "8080:8080"' not in compose
    assert '- "8001:8001"' not in compose
    assert '- "3000:3000"' not in compose
    assert '- "9090:9090"' not in compose
    assert '- "3001:3000"' not in compose


def test_weaviate_auth_defaults_are_internally_consistent():
    compose = _compose_text()
    assert (
        'AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "${WEAVIATE_ANONYMOUS_ACCESS_ENABLED:-false}"'
        in compose
    )
    assert 'AUTHENTICATION_APIKEY_ENABLED: "true"' in compose
    assert (
        'AUTHENTICATION_APIKEY_ALLOWED_KEYS: "${WEAVIATE_API_KEY:-local-dev-weaviate-api-key}"'
        in compose
    )
    assert (
        'WEAVIATE_API_KEY: "${WEAVIATE_API_KEY:-local-dev-weaviate-api-key}"' in compose
    )
    assert "WEAVIATE_ANONYMOUS_ACCESS_ENABLED:-true" not in compose


def test_active_compose_does_not_hardcode_grafana_password_or_discord_ids():
    compose = _compose_text()
    assert 'GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD}"' in compose
    assert 'GF_SECURITY_ADMIN_PASSWORD: "' not in compose.replace(
        'GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD}"', ""
    )
    assert 'DISCORD_TEST_GUILD_ID: "${DISCORD_TEST_GUILD_ID}"' in compose
    assert 'DISCORD_CLIENT_ID: "${DISCORD_CLIENT_ID}"' in compose
    assert 'DISCORD_GUILD_ID: "${DISCORD_GUILD_ID}"' in compose
    for line in compose.splitlines():
        stripped = line.strip()
        if stripped.startswith("DISCORD_") and "=" in stripped and "${" not in stripped:
            raise AssertionError("active Compose has a hardcoded Discord identifier")
