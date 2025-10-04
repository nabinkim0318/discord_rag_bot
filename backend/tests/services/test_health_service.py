"""
Tests for Health service functionality
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.health import (
    health,
    health_check,
    health_check_db,
    health_check_llm,
    health_check_vector_store,
)
from app.main import app


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
        # Mock log directory
        mock_log_dir = MagicMock()
        mock_log_dir.mkdir.return_value = None
        mock_log_dir.__truediv__.return_value = mock_log_dir  # For path operations
        mock_log_dir.write_text.return_value = None
        mock_log_dir.unlink.return_value = None
        mock_get_log_dir.return_value = mock_log_dir

        result = await health_check()

        assert result["status"] == "healthy"
        assert "duration" in result
        assert "checks" in result
        assert "filesystem" in result["checks"]

    @patch("app.core.config.get_log_dir")
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_get_log_dir):
        """Test health check endpoint failure"""
        # Mock log directory failure
        mock_get_log_dir.side_effect = Exception("Directory access failed")

        result = await health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "duration" in result
        assert "Directory access failed" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_db_success(self):
        """Test database health check success"""
        # Mock database session
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (1,)

        result = await health_check_db(mock_session)

        assert result["status"] == "database healthy"
        assert "duration" in result

    @pytest.mark.asyncio
    async def test_health_check_db_failure(self):
        """Test database health check failure"""
        # Mock database session with error
        mock_session = MagicMock()
        mock_session.exec.side_effect = Exception("Database connection failed")

        result = await health_check_db(mock_session)

        assert result["status"] == "database unhealthy"
        assert "error" in result
        assert "duration" in result
        assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_llm_success(self):
        """Test LLM health check success"""
        with (
            patch("app.api.v1.health.settings") as mock_settings,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_settings.OPENAI_API_KEY = "mock_key"
            mock_settings.LLM_MODEL = "gpt-4o-mini"

            response = await health_check_llm()
            # LLM check is currently mocked/disabled, so it should always return healthy
            assert response["status"] == "llm healthy"
            assert "duration" in response
            assert response["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_health_check_llm_no_api_key(self):
        """Test LLM health check with no API key"""
        with patch("app.api.v1.health.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            response = await health_check_llm()
            # Since actual LLM call is commented out, it returns
            # healthy even without API key
            assert response["status"] == "llm healthy"

    @pytest.mark.asyncio
    async def test_health_check_vector_store_success(self):
        """Test vector store health check success"""
        with (
            patch("app.core.weaviate_client.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.health.settings") as mock_settings,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            mock_settings.WEAVIATE_URL = "http://mock-weaviate:8080"

            response = await health_check_vector_store()
            assert response["status"] == "vector store healthy"
            assert "duration" in response
            assert response["service"] == "weaviate"

    @pytest.mark.asyncio
    async def test_health_check_vector_store_unhealthy(self):
        """Test vector store health check unhealthy"""
        with (
            patch("app.core.weaviate_client.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.health.perf_counter", side_effect=[0, 0.1]),
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = False
            mock_get_client.return_value = mock_client

            response = await health_check_vector_store()
            assert response["status"] == "vector store unhealthy"
            assert "Weaviate not ready" in response["error"]

    def test_health_endpoints_integration(self):
        """Test health endpoints via FastAPI client"""
        client = TestClient(app)

        # Test root health endpoint
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Test comprehensive health check (redirects to /api/v1/health/)
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

    def test_health_check_vector_store_endpoint(self):
        """Test vector store health check endpoint"""
        client = TestClient(app)

        response = client.get("/api/v1/health/vector-store")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "duration" in data


if __name__ == "__main__":
    pytest.main([__file__])
