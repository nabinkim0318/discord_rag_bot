"""Regression checks for CI gates and observability truthfulness."""

from __future__ import annotations

import json
import re
from pathlib import Path

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.core import metrics as app_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "main.yml"
PROMETHEUS_DEFAULT = REPO_ROOT / "ops" / "prometheus" / "prometheus.yml"
PROMETHEUS_DISCORD = (
    REPO_ROOT / "ops" / "prometheus" / "scrape.d.discord" / "discord-bot.yml"
)
COMPOSE_PATH = REPO_ROOT / "docker-compose.yaml"
COMPOSE_DISCORD_PATH = REPO_ROOT / "docker-compose.discord.yaml"
ENHANCED_METRICS_PATH = REPO_ROOT / "backend" / "app" / "core" / "enhanced_metrics.py"

PROVISIONED_DASHBOARD_PATH = (
    REPO_ROOT
    / "ops"
    / "grafana"
    / "provisioning"
    / "dashboards"
    / "rag-metrics-dashboard.json"
)
ALERTS_PATH = REPO_ROOT / "ops" / "grafana" / "provisioning" / "alerting" / "alerts.yml"
STALE_DASHBOARD_COPIES = [
    REPO_ROOT / "ops" / "grafana" / "dashboards" / "rag-metrics-dashboard.json",
    REPO_ROOT / "ops" / "grafana" / "dashboards" / "simple-dashboard.json",
]
STALE_ROOT_PROMETHEUS = REPO_ROOT / "prometheus.yml"
SCRAPE_D_MOUNT = "./ops/prometheus/scrape.d:/etc/prometheus/scrape.d:ro"
SCRAPE_D_GLOB = "/etc/prometheus/scrape.d/*.yml"

SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".sqlite3"}

PROMQL_KEYWORDS = {
    "sum",
    "rate",
    "irate",
    "increase",
    "histogram_quantile",
    "clamp_min",
    "clamp_max",
    "vector",
    "avg",
    "min",
    "max",
    "count",
    "stddev",
    "stdvar",
    "by",
    "without",
    "on",
    "ignoring",
    "group_left",
    "group_right",
    "or",
    "and",
    "unless",
    "bool",
    "offset",
    "inf",
    "nan",
    "le",
}

# Prometheus self-scrape series that provisioned dashboards may reference.
# Application HTTP telemetry such as http_requests_total is not exposed and
# must not be allow-listed just to keep a panel.
KNOWN_EXTERNAL_METRICS = {
    "up",
}

IDENT_RE = re.compile(r"(?<![A-Za-z0-9_])([a-zA-Z_:][a-zA-Z0-9_:]*)")
FAILURE_COUNTER_BARE_RE = re.compile(r"rag_query_failures(?!_total)\b")


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _iter_repo_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def _bandit_command_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\bbandit\s+-", line) and not line.strip().startswith("#")
    ]


def _exposed_counter_name(name: str) -> str:
    return name if name.endswith("_total") else f"{name}_total"


def _application_exposed_metric_names() -> set[str]:
    names: set[str] = set()
    for value in vars(app_metrics).values():
        if isinstance(value, Counter):
            names.add(_exposed_counter_name(value._name))
        elif isinstance(value, Histogram):
            names.update(
                {
                    f"{value._name}_bucket",
                    f"{value._name}_count",
                    f"{value._name}_sum",
                }
            )
        elif isinstance(value, Gauge):
            names.add(value._name)
    names.update(KNOWN_EXTERNAL_METRICS)
    return names


def _dashboard_exprs(payload: dict) -> list[str]:
    exprs: list[str] = []
    for panel in payload.get("panels", []):
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                exprs.append(expr)
    return exprs


def _metric_tokens(expr: str) -> set[str]:
    tokens = set()
    stripped = re.sub(r"\{[^}]*\}", " ", expr)
    for match in IDENT_RE.finditer(stripped):
        token = match.group(1)
        if token.lower() in PROMQL_KEYWORDS:
            continue
        if re.fullmatch(r"[0-9]+", token):
            continue
        if "_" in token or token == "up":
            tokens.add(token)
    return tokens


def test_workflow_is_named_ci_not_cicd():
    text = _workflow_text()
    assert "name: Main CI Pipeline" in text
    assert "CI/CD" not in text


def test_workflow_eslint_is_a_blocking_gate():
    text = _workflow_text()
    assert "npm run lint" in text
    frontend_pkg = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    assert "lint" in frontend_pkg["scripts"]
    assert "eslint" in frontend_pkg["scripts"]["lint"]
    for line in text.splitlines():
        stripped = line.strip()
        if "eslint" in stripped or stripped == "npm run lint":
            assert "|| true" not in stripped
            assert "||true" not in stripped.replace(" ", "")


def test_workflow_python_format_is_check_only():
    text = _workflow_text()
    mutating = []
    for line in text.splitlines():
        stripped = line.strip()
        if "ruff format" not in stripped:
            continue
        assert "--check" in stripped, stripped
        if (
            re.search(r"ruff format(?:\s+\S+)*\s+\.(?!\S)", stripped)
            and "--check" not in stripped
        ):
            mutating.append(stripped)
    assert mutating == []
    assert "ruff format --check" in text
    assert "isort --check-only" in text
    assert "ruff check" in text


def test_workflow_bandit_policy_is_blocking_high_high():
    text = _workflow_text()
    assert "name: Backend Security Scan (Bandit high/high)" in text
    bandit_lines = _bandit_command_lines(text)
    assert bandit_lines, "expected Bandit commands in the workflow"
    assert any("--exit-zero" in line for line in bandit_lines)
    gate_lines = [
        line
        for line in bandit_lines
        if "--severity-level high" in line and "--confidence-level high" in line
    ]
    assert gate_lines, "expected a high-severity/high-confidence Bandit gate"
    for line in gate_lines:
        assert "|| true" not in line
        assert "--exit-zero" not in line
        assert "-r app" in line
        assert "rag_agent" not in line
        assert "bots" not in line
    for line in bandit_lines:
        assert "|| true" not in line
        assert "-r app" in line
        assert "rag_agent" not in line
        assert "bots" not in line


def test_integration_summary_does_not_claim_informational_security_passed():
    text = _workflow_text()
    summary = text.split("All checks passed", 1)[1]
    assert "Security scan: PASSED" not in summary
    assert "Security Scan: PASSED" not in summary
    assert "Backend Bandit high-severity/high-confidence gate: PASSED" in summary
    assert "Frontend tests, Prettier, and ESLint: PASSED" in summary
    assert "CI/CD" not in summary
    bandit_summary_lines = [line for line in summary.splitlines() if "Bandit" in line]
    assert bandit_summary_lines
    for line in bandit_summary_lines:
        assert "rag_agent" not in line
        assert "bots" not in line


def test_grafana_dashboard_json_parses():
    payload = json.loads(PROVISIONED_DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload.get("panels"), PROVISIONED_DASHBOARD_PATH


def test_failure_panel_uses_exposed_counter_name():
    exposed = None
    registry = CollectorRegistry()
    counter = Counter(
        "rag_query_failures",
        "Number of failed RAG queries",
        ["endpoint", "error_type"],
        registry=registry,
    )
    counter.labels(endpoint="/api/v1/rag/", error_type="test").inc()
    text = generate_latest(registry).decode("utf-8")
    assert "rag_query_failures_total" in text
    assert CONTENT_TYPE_LATEST
    exposed = "rag_query_failures_total"

    provisioned = PROVISIONED_DASHBOARD_PATH.read_text(encoding="utf-8")
    assert exposed in provisioned
    assert not FAILURE_COUNTER_BARE_RE.search(provisioned)


def test_dashboard_metric_references_are_exposed():
    allowed = _application_exposed_metric_names()
    assert "http_requests_total" not in allowed
    unknown: list[str] = []
    payload = json.loads(PROVISIONED_DASHBOARD_PATH.read_text(encoding="utf-8"))
    for expr in _dashboard_exprs(payload):
        for token in _metric_tokens(expr):
            if token not in allowed:
                unknown.append(f"{PROVISIONED_DASHBOARD_PATH.name}: {token} in {expr}")
    alerts = ALERTS_PATH.read_text(encoding="utf-8")
    for expr in re.findall(r"expr:\s*(.+)", alerts):
        for token in _metric_tokens(expr):
            if token not in allowed:
                unknown.append(f"{ALERTS_PATH.name}: {token} in {expr}")
    assert unknown == []


def test_provisioned_dashboards_do_not_query_http_requests_total():
    provisioned = PROVISIONED_DASHBOARD_PATH.read_text(encoding="utf-8")
    assert "http_requests_total" not in provisioned
    alerts = ALERTS_PATH.read_text(encoding="utf-8")
    assert "http_requests_total" not in alerts


def test_enhanced_metrics_module_removed_and_unreferenced():
    assert not ENHANCED_METRICS_PATH.exists()
    production_roots = [
        REPO_ROOT / "backend" / "app",
        REPO_ROOT / "rag_agent",
        REPO_ROOT / "bots",
    ]
    references = []
    for root in production_roots:
        for path in root.rglob("*.py"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            if "enhanced_metrics" in text:
                references.append(str(path.relative_to(REPO_ROOT)))
    assert references == []


def test_default_prometheus_config_does_not_scrape_optional_bot():
    default_cfg = PROMETHEUS_DEFAULT.read_text(encoding="utf-8")
    assert "bot:9109" not in default_cfg
    assert "discord-bot" not in default_cfg
    assert "scrape_config_files:" in default_cfg
    assert SCRAPE_D_GLOB in default_cfg
    scrape_d = REPO_ROOT / "ops" / "prometheus" / "scrape.d"
    extra_yml = list(scrape_d.glob("*.yml")) + list(scrape_d.glob("*.yaml"))
    assert extra_yml == []
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    assert SCRAPE_D_MOUNT in compose
    assert "scrape.d.discord" not in compose
    assert "profiles:" in compose
    assert "- discord" in compose


def test_optional_discord_prometheus_config_targets_bot_9109():
    assert PROMETHEUS_DISCORD.exists()
    discord_cfg = PROMETHEUS_DISCORD.read_text(encoding="utf-8")
    uncommented = "\n".join(
        line
        for line in discord_cfg.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    assert "global:" not in uncommented
    assert "rule_files:" not in uncommented
    assert "scrape_config_files:" not in uncommented
    assert "bot:9109" in uncommented
    assert 'job_name: "discord-bot"' in uncommented
    assert uncommented.lstrip().startswith("scrape_configs:")
    overlay = COMPOSE_DISCORD_PATH.read_text(encoding="utf-8")
    assert "scrape.d.discord:/etc/prometheus/scrape.d:ro" in overlay
    assert "prometheus.yml" not in overlay
    assert "profiles:" not in overlay or "discord" in overlay


def test_stale_unprovisioned_observability_duplicates_are_removed():
    for path in STALE_DASHBOARD_COPIES:
        assert not path.exists(), path
    assert not STALE_ROOT_PROMETHEUS.exists()


def test_bot_9109_only_appears_in_intentional_discord_path():
    allowed = {
        PROMETHEUS_DISCORD.resolve(),
        COMPOSE_DISCORD_PATH.resolve(),
        Path(__file__).resolve(),
    }
    hits = []
    for path in _iter_repo_files():
        if path.suffix not in {".yml", ".yaml", ".py", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "bot:9109" not in text:
            continue
        if path.resolve() in allowed:
            continue
        hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == []
