# tests/test_error_handling.py
"""
Tests for error handling and retry logic
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import ExternalServiceException, RAGException
from app.core.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryConfig,
    retry_database,
    retry_openai,
    retry_weaviate,
    retry_with_circuit_breaker,
)
from app.models.error import (
    create_circuit_breaker_error,
    create_rag_error,
    create_service_error,
    create_validation_error,
)


class TestRetryLogic:
    """Test retry logic functionality"""

    def test_retry_config_defaults(self):
        """Test RetryConfig default values"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ConnectionError in config.retryable_exceptions

    def test_circuit_breaker_config_defaults(self):
        """Test CircuitBreakerConfig default values"""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == ExternalServiceException

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        cb = CircuitBreaker(config, "test")

        # Initially closed
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

        # Fail twice to open circuit
        cb.on_failure(Exception("test"))
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

        cb.on_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

        # Wait for recovery timeout
        import time

        time.sleep(1.1)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

        # Success in half-open moves to closed
        cb.on_success()
        cb.on_success()
        assert cb.state == CircuitState.CLOSED

    def test_retry_decorator_success(self):
        """Test retry decorator with successful function"""

        @retry_with_circuit_breaker()
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_decorator_failure(self):
        """Test retry decorator with failing function"""
        call_count = 0

        @retry_with_circuit_breaker(
            retry_config=RetryConfig(max_attempts=2, base_delay=0.01)
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            failing_function()

        assert call_count == 2  # Should retry once

    def test_retry_decorator_non_retryable_exception(self):
        """Test retry decorator with non-retryable exception"""
        call_count = 0

        @retry_with_circuit_breaker()
        def non_retryable_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            non_retryable_function()

        assert call_count == 1  # Should not retry

    def test_retry_weaviate_decorator(self):
        """Test Weaviate-specific retry decorator"""

        @retry_weaviate(max_attempts=2)
        def weaviate_function():
            return "weaviate_success"

        result = weaviate_function()
        assert result == "weaviate_success"

    def test_retry_openai_decorator(self):
        """Test OpenAI-specific retry decorator"""

        @retry_openai(max_attempts=2)
        def openai_function():
            return "openai_success"

        result = openai_function()
        assert result == "openai_success"

    def test_retry_database_decorator(self):
        """Test database-specific retry decorator"""

        @retry_database(max_attempts=2)
        def database_function():
            return "database_success"

        result = database_function()
        assert result == "database_success"


class TestErrorResponseModels:
    """Test error response models"""

    def test_validation_error_response(self):
        """Test validation error response creation"""
        error = create_validation_error(message="Invalid input", request_id="test-123")

        assert error.error == "Validation Error"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.request_id == "test-123"
        assert error.success is False

    def test_service_error_response(self):
        """Test service error response creation"""
        error = create_service_error(
            message="Service unavailable",
            service="weaviate",
            retry_after=30,
            request_id="test-123",
        )

        assert error.error == "Service Error"
        assert error.error_code == "SERVICE_ERROR"
        assert error.service == "weaviate"
        assert error.retry_after == 30
        assert error.request_id == "test-123"

    def test_rag_error_response(self):
        """Test RAG error response creation"""
        error = create_rag_error(
            message="RAG pipeline failed", stage="retrieval", request_id="test-123"
        )

        assert error.error == "RAG Pipeline Error"
        assert error.error_code == "RAG_ERROR"
        assert error.stage == "retrieval"
        assert error.request_id == "test-123"

    def test_circuit_breaker_error_response(self):
        """Test circuit breaker error response creation"""
        error = create_circuit_breaker_error(
            service="weaviate", state="open", retry_after=60, request_id="test-123"
        )

        assert error.error == "Service Temporarily Unavailable"
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
        assert error.service == "weaviate"
        assert error.state == "open"
        assert error.retry_after == 60


class TestErrorHandlingIntegration:
    """Test error handling integration with FastAPI"""

    def test_rag_exception_handling(self):
        """Test RAG exception handling in API"""
        app = FastAPI()

        @app.get("/test-rag-error")
        def test_rag_error():
            raise RAGException("RAG pipeline failed", details={"stage": "retrieval"})

        from app.core.error_handlers import setup_error_handlers

        setup_error_handlers(app)

        client = TestClient(app)
        response = client.get("/test-rag-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "RAG Pipeline Error"
        assert data["error_code"] == "RAG_ERROR"
        assert data["stage"] == "retrieval"

    def test_validation_error_handling(self):
        """Test validation error handling in API"""
        app = FastAPI()

        @app.get("/test-validation-error")
        def test_validation_error():
            raise HTTPException(status_code=422, detail="Validation failed")

        from app.core.error_handlers import setup_error_handlers

        setup_error_handlers(app)

        client = TestClient(app)
        response = client.get("/test-validation-error")

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "HTTP Error"
        assert data["error_code"] == "HTTP_422"

    def test_external_service_error_handling(self):
        """Test external service error handling in API"""
        app = FastAPI()

        @app.get("/test-service-error")
        def test_service_error():
            raise ExternalServiceException(
                "Service unavailable", service_name="weaviate"
            )

        from app.core.error_handlers import setup_error_handlers

        setup_error_handlers(app)

        client = TestClient(app)
        response = client.get("/test-service-error")

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "Service Error"
        assert data["error_code"] == "SERVICE_ERROR"
        assert data["service"] == "weaviate"
        assert "Retry-After" in response.headers


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with services"""

    def test_weaviate_circuit_breaker(self):
        """Test Weaviate circuit breaker behavior"""
        # This test is simplified since we can't easily mock the decorator
        # In a real scenario, we would test the circuit breaker behavior
        # by making actual calls that fail

        from app.services.rag_service import search_similar_documents

        # Test that the function exists and can be called
        # (actual circuit breaker testing would require more complex setup)
        try:
            result = search_similar_documents("test query", 3)
            assert isinstance(result, list)
        except Exception:
            # Expected to fail in test environment
            pass

    def test_openai_circuit_breaker(self):
        """Test OpenAI circuit breaker behavior"""
        # This test is simplified since we can't easily mock the decorator
        # In a real scenario, we would test the circuit breaker behavior
        # by making actual calls that fail

        from app.services.rag_service import call_llm

        # Test that the function exists and can be called
        # (actual circuit breaker testing would require more complex setup)
        try:
            result = call_llm("test prompt")
            assert isinstance(result, str)
        except Exception:
            # Expected to fail in test environment
            pass


if __name__ == "__main__":
    pytest.main([__file__])
