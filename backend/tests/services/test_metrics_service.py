"""
Tests for Metrics service functionality
"""

from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import Counter, Gauge, Histogram

from app.core.metrics import (  # Metrics instances
    circuit_breaker_state,
    create_counter,
    create_gauge,
    create_histogram,
    feedback_counter,
    feedback_satisfaction_rate,
    feedback_submissions,
    health_check_counter,
    health_check_db_counter,
    health_check_db_failures,
    health_check_db_latency,
    health_check_llm_counter,
    health_check_llm_failures,
    health_check_llm_latency,
    health_check_vector_store_counter,
    health_check_vector_store_failures,
    health_check_vector_store_latency,
    rag_failures_total,
    rag_pipeline_latency,
    rag_query_counter,
    rag_query_failures,
    rag_query_latency,
    rag_query_metric,
    rag_requests_total,
    rag_retrieval_hit_counter,
    rag_retriever_topk,
    record_failure_metric,
    record_feedback_metric,
    record_prompt_version,
    record_rag_pipeline_latency,
    record_rag_request,
    record_retrieval_hit,
    record_retriever_topk,
)


class TestMetricsService:
    """Test cases for metrics service functionality"""

    def test_create_counter(self):
        """Test counter metric creation"""
        counter = create_counter("test_counter", "Test counter metric")
        assert isinstance(counter, Counter)
        assert counter._name == "test_counter"
        assert counter._documentation == "Test counter metric"

    def test_create_gauge(self):
        """Test gauge metric creation"""
        gauge = create_gauge("test_gauge", "Test gauge metric")
        assert isinstance(gauge, Gauge)
        assert gauge._name == "test_gauge"
        assert gauge._documentation == "Test gauge metric"

    def test_create_histogram(self):
        """Test histogram metric creation"""
        histogram = create_histogram("test_histogram", "Test histogram metric")
        assert isinstance(histogram, Histogram)
        assert histogram._name == "test_histogram"
        assert histogram._documentation == "Test histogram metric"

    def test_rag_query_metric(self):
        """Test RAG query metric recording"""
        mock_info = MagicMock()
        mock_info.modified_path = "/api/v1/rag/"
        mock_info.method = "POST"
        mock_info.duration = 0.5

        # Mock the counter to track calls
        with patch.object(rag_query_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            rag_query_metric(mock_info)

            # Verify the counter was called
            mock_labels.assert_called_once_with(method="POST", endpoint="/api/v1/rag/")
            mock_counter.inc.assert_called_once()

    def test_record_feedback_metric(self):
        """Test feedback metric recording"""
        with patch.object(feedback_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_feedback_metric("like")

            mock_labels.assert_called_once_with(type="like")
            mock_counter.inc.assert_called_once()

    def test_record_failure_metric(self):
        """Test failure metric recording"""
        with patch.object(rag_query_failures, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_failure_metric("/api/v1/rag/", "LLM_ERROR")

            mock_labels.assert_called_once_with(
                endpoint="/api/v1/rag/", error_type="LLM_ERROR"
            )
            mock_counter.inc.assert_called_once()
        # Additional verification can be added here if needed

    def test_record_rag_request(self):
        """Test RAG request metric recording"""
        with patch.object(rag_requests_total, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_rag_request("/api/v1/enhanced-rag/")

            mock_labels.assert_called_once_with(endpoint="/api/v1/enhanced-rag/")
            mock_counter.inc.assert_called_once()

    def test_record_rag_pipeline_latency(self):
        """Test RAG pipeline latency recording"""
        with patch.object(rag_pipeline_latency, "observe") as mock_observe:
            record_rag_pipeline_latency(1.23)
            mock_observe.assert_called_once_with(1.23)

    def test_record_retrieval_hit(self):
        """Test retrieval hit metric recording"""
        with patch.object(rag_retrieval_hit_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_retrieval_hit(True)

            mock_labels.assert_called_once_with(hit="true")
            mock_counter.inc.assert_called_once()

        # Test with False value
        with patch.object(rag_retrieval_hit_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_retrieval_hit(False)

            mock_labels.assert_called_once_with(hit="false")
            mock_counter.inc.assert_called_once()

    def test_record_retriever_topk(self):
        """Test retriever top-k metric recording"""
        with patch.object(rag_retriever_topk, "observe") as mock_observe:
            record_retriever_topk(5)
            mock_observe.assert_called_once_with(5.0)
            mock_observe.reset_mock()

            record_retriever_topk("invalid")  # Should not raise error
            mock_observe.assert_not_called()

    def test_record_prompt_version(self):
        """Test prompt version metric recording"""
        record_prompt_version("v1.1")
        # This function doesn't return anything, just ensures it doesn't raise an error
        assert True

    def test_metrics_instances_exist(self):
        """Test that all metric instances are properly initialized"""
        # Test counter metrics
        assert isinstance(rag_query_counter, Counter)
        assert isinstance(rag_query_failures, Counter)
        assert isinstance(feedback_counter, Counter)
        assert isinstance(feedback_submissions, Counter)
        assert isinstance(rag_requests_total, Counter)
        assert isinstance(rag_failures_total, Counter)
        assert isinstance(rag_retrieval_hit_counter, Counter)
        assert isinstance(health_check_counter, Counter)
        assert isinstance(health_check_db_counter, Counter)
        assert isinstance(health_check_llm_counter, Counter)
        assert isinstance(health_check_vector_store_counter, Counter)
        assert isinstance(health_check_db_failures, Counter)
        assert isinstance(health_check_llm_failures, Counter)
        assert isinstance(health_check_vector_store_failures, Counter)

        # Test histogram metrics
        assert isinstance(rag_query_latency, Histogram)
        assert isinstance(rag_pipeline_latency, Histogram)
        assert isinstance(rag_retriever_topk, Histogram)
        assert isinstance(health_check_db_latency, Histogram)
        assert isinstance(health_check_llm_latency, Histogram)
        assert isinstance(health_check_vector_store_latency, Histogram)

        # Test gauge metrics
        assert isinstance(feedback_satisfaction_rate, Gauge)
        assert isinstance(circuit_breaker_state, Gauge)

    def test_metrics_recording_integration(self):
        """Test integrated metrics recording workflow"""
        # Record a complete RAG request
        mock_info = MagicMock()
        mock_info.modified_path = "/api/v1/rag/"
        mock_info.method = "POST"
        mock_info.duration = 0.5

        with (
            patch.object(rag_query_counter, "labels") as mock_query_labels,
            patch.object(rag_requests_total, "labels") as mock_request_labels,
            patch.object(rag_retrieval_hit_counter, "labels") as mock_hit_labels,
        ):
            mock_query_counter = MagicMock()
            mock_request_counter = MagicMock()
            mock_hit_counter = MagicMock()

            mock_query_labels.return_value = mock_query_counter
            mock_request_labels.return_value = mock_request_counter
            mock_hit_labels.return_value = mock_hit_counter

            rag_query_metric(mock_info)
            record_rag_request("/api/v1/rag/")
            record_rag_pipeline_latency(0.5)
            record_retrieval_hit(True)
            record_retriever_topk(5)

            # Verify all metrics were called
            mock_query_counter.inc.assert_called_once()
            mock_request_counter.inc.assert_called_once()
            mock_hit_counter.inc.assert_called_once()
        # Additional verification can be added here if needed

    def test_metrics_error_handling(self):
        """Test metrics recording with error scenarios"""
        # Test with invalid inputs
        record_retriever_topk("invalid")  # Should not raise error
        record_retriever_topk(-1)  # Should not raise error

        # Test feedback with invalid type
        with patch.object(feedback_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            record_feedback_metric("invalid_type")

            mock_labels.assert_called_once_with(type="invalid_type")
            mock_counter.inc.assert_called_once()

    def test_metrics_counter_increment(self):
        """Test that counters increment correctly"""
        with patch.object(rag_query_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            # Record multiple events with valid RAG paths
            for i in range(3):
                mock_info = MagicMock()
                mock_info.modified_path = "/api/v1/rag/"  # Valid RAG path
                mock_info.method = "GET"
                mock_info.duration = 0.1 * i
                rag_query_metric(mock_info)

            # Check that counter was called 3 times
            assert mock_labels.call_count == 3
            assert mock_counter.inc.call_count == 3

    def test_metrics_gauge_setting(self):
        """Test that gauges can be set correctly"""
        # Set satisfaction rate
        feedback_satisfaction_rate.set(85.5)

        # Set circuit breaker state (without labels for now)
        # circuit_breaker_state.labels(state="closed").set(1)  # 1 = closed, 0 = open

    def test_metrics_timing(self):
        """Test that timing metrics work correctly"""
        with patch.object(rag_pipeline_latency, "observe") as mock_observe:
            # Record pipeline latency
            record_rag_pipeline_latency(1.5)
            mock_observe.assert_called_once_with(1.5)

    def test_metrics_labels(self):
        """Test that metrics with labels work correctly"""
        with patch.object(feedback_counter, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            # Test feedback counter with different types
            record_feedback_metric("like")
            record_feedback_metric("dislike")
            record_feedback_metric("like")  # Another like

            # Verify calls were made
            assert mock_labels.call_count == 3
            assert mock_counter.inc.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__])
