#!/usr/bin/env python3
"""
Simple Metrics Dashboard (without Docker)
"""
from datetime import datetime

import requests


def get_metrics():
    """Get metrics from the backend"""
    try:
        response = requests.get("http://localhost:8001/metrics")
        if response.status_code == 200:
            return response.text
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None


def parse_metrics(metrics_text):
    """Parse metrics text"""
    metrics = {}
    lines = metrics_text.split("\n")

    for line in lines:
        if line.startswith("#") or not line.strip():
            continue

        if " " in line:
            parts = line.split(" ")
            if len(parts) >= 2:
                metric_name = parts[0]
                try:
                    value = float(parts[1])
                    metrics[metric_name] = value
                except ValueError:
                    continue

    return metrics


def display_dashboard():
    """Display simple dashboard"""
    print("=" * 60)
    print("📊 RAG Bot Metrics Dashboard")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    metrics_text = get_metrics()
    if not metrics_text:
        print("❌ Cannot connect to the backend API.")
        print(
            "   Start the backend: cd backend && poetry run uvicorn app.main:app \
            --host 0.0.0.0 --port 8001 --reload"
        )
        return

    metrics = parse_metrics(metrics_text)

    # RAG related metrics
    print("🤖 RAG Metrics:")
    rag_metrics = {k: v for k, v in metrics.items() if "rag_" in k}
    if rag_metrics:
        for name, value in rag_metrics.items():
            if "count" in name or "total" in name:
                print(f"  📈 {name}: {int(value)}")
            elif "latency" in name or "seconds" in name:
                print(f"  ⏱️  {name}: {value:.3f}s")
            else:
                print(f"  📊 {name}: {value}")
    else:
        print("  📊 No RAG queries yet.")

    print()

    # Health metrics
    print("🏥 Health Metrics:")
    health_metrics = {k: v for k, v in metrics.items() if "health_" in k}
    if health_metrics:
        for name, value in health_metrics.items():
            if "failures" in name:
                status = "❌" if value > 0 else "✅"
                print(f"  {status} {name}: {int(value)}")
            else:
                print(f"  📊 {name}: {int(value)}")
    else:
        print("  📊 No health metrics")

    print()

    # Python metrics
    print("🐍 Python Metrics:")
    python_metrics = {k: v for k, v in metrics.items() if "python_" in k}
    if python_metrics:
        for name, value in python_metrics.items():
            if "gc_" in name:
                print(f"  🗑️  {name}: {int(value)}")
            else:
                print(f"  📊 {name}: {value}")

    print()
    print("=" * 60)
    print("💡 Tips:")
    print("  - RAG queries update metrics")
    print("  - Docker to use Grafana dashboard")
    print("  - http://localhost:8001/metrics to see raw data")


if __name__ == "__main__":
    display_dashboard()
