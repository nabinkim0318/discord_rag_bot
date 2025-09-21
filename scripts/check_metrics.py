#!/usr/bin/env python3
"""
간단한 metrics 확인 스크립트
"""
from datetime import datetime

import requests


def check_metrics():
    """백엔드 API에서 metrics 확인"""
    try:
        # 백엔드 API health check
        health_response = requests.get("http://localhost:8001/health")
        print(f"🏥 Backend Health: {health_response.status_code}")

        # Metrics endpoint
        metrics_response = requests.get("http://localhost:8001/metrics")
        if metrics_response.status_code == 200:
            print("📊 Metrics available at: http://localhost:8001/metrics")

            # 간단한 metrics 파싱
            metrics_text = metrics_response.text
            lines = metrics_text.split("\n")

            print("\n📈 Key Metrics:")
            for line in lines:
                if any(
                    keyword in line
                    for keyword in [
                        "rag_query_total",
                        "rag_pipeline_latency",
                        "rag_retrieval_hits",
                        "http_requests_total",
                    ]
                ):
                    if not line.startswith("#"):
                        print(f"  {line}")
        else:
            print(f"❌ Metrics not available: {metrics_response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Backend API not running. Start with:")
        print(
            "cd backend && poetry run uvicorn app.main:app \
            --host 0.0.0.0 --port 8001 --reload"
        )


if __name__ == "__main__":
    print(f"🔍 Checking metrics at {datetime.now()}")
    check_metrics()
