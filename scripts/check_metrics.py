#!/usr/bin/env python3
"""
Simple metrics check script
"""
from datetime import datetime

import requests
from rag_agent.core.logging import logger


def check_metrics():
    """Check metrics from backend API"""
    try:
        # Backend API health check
        health_response = requests.get("http://localhost:8001/health")
        logger.info(f"🏥 Backend Health: {health_response.status_code}")

        # Metrics endpoint
        metrics_response = requests.get("http://localhost:8001/metrics")
        if metrics_response.status_code == 200:
            logger.info("📊 Metrics available at: http://localhost:8001/metrics")

            # Simple metrics parsing
            metrics_text = metrics_response.text
            lines = metrics_text.split("\n")

            logger.info("\n📈 Key Metrics:")
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
                        logger.info(f"  {line}")
        else:
            logger.warning(f"❌ Metrics not available: {metrics_response.status_code}")

    except requests.exceptions.ConnectionError:
        logger.warning("❌ Backend API not running. Start with:")
        logger.warning(
            "cd backend && poetry run uvicorn app.main:app \
            --host 0.0.0.0 --port 8001 --reload"
        )


if __name__ == "__main__":
    logger.info(f"🔍 Checking metrics at {datetime.now()}")
    check_metrics()
