"""
Tests for Health service functionality
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.health import (
    PUBLIC_DB_UNAVAILABLE,
    PUBLIC_FILESYSTEM_UNAVAILABLE,
    PUBLIC_VECTOR_UNAVAILABLE,
    health,
    health_check,
    health_check_db,
    health_check_llm,
    health_check_vector_store,
)
from app.main import app


def _body(response):
    if isinstance(response, dict):
        return response
    return json.loads(response.body)


class TestHealthService:
    """Test cases for health service functionality"""

    def test_health_root(self):
        """Test basic health endpoint"""
        result = health()

        assert result == {"status": "ok"}

    @patch("app.core.config.get_log_dir")
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_get_log_dir):
        """Test health check endpoint success"""
        mock_log_dir = MagicMock()
        mock_log_dir.mkdir.return_value = None
        mock_log_dir.__truediv__.return_value = mock_log_dir
        mock_log_dir.write_text.return_value = None
        mock_log_dir.unlink.return_value = None
        mock_get_log_dir.return_value = mock_log_dir

        result = await health_check()
        payload = _body(result)

        assert result.status_code == 200
        assert payload["status"] == "healthy"
        assert "duration" in payload
        assert "checks" in payload
        assert "filesystem" in payload["checks"]

    @patch("app.core.config.get_log_dir")
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_get_log_dir):
        """Test health check endpoint failure"""
        mock_get_log_dir.side_effect = Exception("Directory access failed")

        result = await health_check()
        payload = _body(result)

        assert result.status_code == 503
        assert payload["status"] == "unhealthy"
        assert payload["error"] == PUBLIC_FILESYSTEM_UNAVAILABLE
        assert "Directory access failed" not in json.dumps(payload)
        assert "duration" in payload

    @pytest.mark.asyncio
    async def test_health_check_db_success(self):
        """Test database health check success"""
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)

        result = await health_check_db(mock_session)
        payload = _body(result)

        assert result.status_code == 200
        assert payload["status"] == "database healthy"
        assert "duration" in payload

    @pytest.mark.asyncio
    async def test_health_check_db_failure(self):
        """Test database health check failure"""
        mock_session = MagicMock()
        mock_session.exec.side_effect = Exception("Database connection failed")

        result = await health_check_db(mock_session)
        payload = _body(result)

        assert result.status_code == 503
        assert payload["status"] == "database unhealthy"
        assert payload["error"] == PUBLIC_DB_UNAVAILABLE
        assert "Database connection failed" not in json.dumps(payload)
        assert "duration" in payload

    @pytest.mark.asyncio
    async def test_health_check_llm_success(self):
        """Test LLM health reports configuration without implying a live probe."""
        with (
            patch("app.api.v1.health.settings") as mock_settings,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_settings.OPENAI_API_KEY = "mock_key"
            mock_settings.AZURE_OPENAI_API_KEY = None
            mock_settings.AZURE_OPENAI_ENDPOINT = None
            mock_settings.LLM_MODEL = "gpt-4o-mini"
            mock_settings.HEALTH_LLM_PROBE_ENABLED = False

            response = await health_check_llm()
            payload = _body(response)
            assert response.status_code == 200
            assert payload["status"] == "configured"
            assert payload["probe"] == "not_performed"
            assert payload["model"] == "gpt-4o-mini"
            assert "duration" in payload

    @pytest.mark.asyncio
    async def test_health_check_llm_no_api_key(self):
        """Test LLM health check with no API key"""
        with patch("app.api.v1.health.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            mock_settings.AZURE_OPENAI_API_KEY = None
            mock_settings.AZURE_OPENAI_ENDPOINT = None
            mock_settings.LLM_MODEL = "gpt-4o-mini"
            mock_settings.HEALTH_LLM_PROBE_ENABLED = False
            response = await health_check_llm()
            payload = _body(response)
            assert response.status_code == 200
            assert payload["status"] == "not_configured"
            assert payload["probe"] == "not_performed"

    @pytest.mark.asyncio
    async def test_health_check_vector_store_success(self):
        """Test vector store health check success"""
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.health.settings") as mock_settings,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            mock_settings.WEAVIATE_URL = "http://mock-weaviate:8080"

            response = await health_check_vector_store()
            payload = _body(response)
            assert response.status_code == 200
            assert payload["status"] == "vector store healthy"
            assert "duration" in payload
            assert payload["service"] == "weaviate"

    @pytest.mark.asyncio
    async def test_health_check_vector_store_unhealthy(self):
        """Test vector store health check unhealthy"""
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = False
            mock_get_client.return_value = mock_client

            response = await health_check_vector_store()
            payload = _body(response)
            assert response.status_code == 503
            assert payload["status"] == "vector store unhealthy"
            assert payload["error"] == PUBLIC_VECTOR_UNAVAILABLE

    def test_health_endpoints_integration(self):
        """Test health endpoints via FastAPI client"""
        client = TestClient(app)

        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        response = client.get("/api/v1/health", follow_redirects=False)
        assert response.status_code == 307  # Redirect

    def test_health_check_db_endpoint(self):
        """Test database health check endpoint"""
        client = TestClient(app)

        response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "duration" in data

    def test_health_check_llm_endpoint(self):
        """Test LLM health check endpoint"""
        client = TestClient(app)

        response = client.get("/api/v1/health/llm")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "duration" in data
        assert data["probe"] == "not_performed"

    def test_health_check_vector_store_endpoint(self):
        """Test vector store health check endpoint"""
        client = TestClient(app)

        with patch("app.api.v1.health.get_weaviate_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/health/vector-store")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "duration" in data


if __name__ == "__main__":
    pytest.main([__file__])
