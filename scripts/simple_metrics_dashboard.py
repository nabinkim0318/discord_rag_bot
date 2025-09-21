#!/usr/bin/env python3
"""
간단한 Metrics 대시보드 (Docker 없이)
"""
from datetime import datetime

import requests


def get_metrics():
    """백엔드에서 metrics 가져오기"""
    try:
        response = requests.get("http://localhost:8001/metrics")
        if response.status_code == 200:
            return response.text
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None


def parse_metrics(metrics_text):
    """Metrics 텍스트 파싱"""
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
    """간단한 대시보드 표시"""
    print("=" * 60)
    print("📊 RAG Bot Metrics Dashboard")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    metrics_text = get_metrics()
    if not metrics_text:
        print("❌ 백엔드 API에 연결할 수 없습니다.")
        print(
            "   백엔드를 시작하세요: cd backend && poetry run uvicorn app.main:app \
            --host 0.0.0.0 --port 8001 --reload"
        )
        return

    metrics = parse_metrics(metrics_text)

    # RAG 관련 metrics
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
        print("  📊 아직 RAG 쿼리가 없습니다.")

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
        print("  📊 Health metrics 없음")

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
    print("  - RAG 쿼리를 실행하면 metrics가 업데이트됩니다")
    print("  - Docker를 설치하면 Grafana 대시보드를 사용할 수 있습니다")
    print("  - http://localhost:8001/metrics 에서 원시 데이터 확인 가능")


if __name__ == "__main__":
    display_dashboard()
