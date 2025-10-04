"""
Tests for Feedback service functionality
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.feedback_service import FeedbackService


class TestFeedbackService:
    """Test Feedback service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.feedback_service = FeedbackService()
        self.test_query_id = "test-query-123"
        self.test_user_id = "user-456"
        self.test_score = "up"
        self.test_comment = "This was helpful!"

    @patch("app.services.feedback_service.FeedbackService._query_exists")
    @patch("app.services.feedback_service.FeedbackService._feedback_exists")
    def test_submit_feedback_success(self, mock_feedback_exists, mock_query_exists):
        """Test successful feedback submission"""
        # Mock the helper methods directly
        mock_query_exists.return_value = True  # Query exists
        mock_feedback_exists.return_value = False  # Feedback doesn't exist

        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (score column exists)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
            (4, "feedback", "TEXT", 0, None, 0),
            (5, "comment", "TEXT", 0, None, 0),
            (6, "created_at", "DATETIME", 0, None, 0),
        ]

        mock_insert_result = MagicMock()
        mock_insert_result.rowcount = 1

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_insert_result,  # Insert feedback
        ]

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )

        assert success is True
        assert message == "Feedback submitted successfully"

        # Verify database operations
        # Note: submit_feedback creates 2 separate connections
        # 1. For PRAGMA table_info
        # 2. For INSERT statement
        assert mock_engine.connect.call_count == 2  # Two separate connections
        mock_conn.commit.assert_called_once()

    @patch("app.services.feedback_service.engine")
    def test_submit_feedback_invalid_score(self, mock_engine):
        """Test feedback submission with invalid score"""
        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, "invalid_score", self.test_comment
        )

        assert success is False
        assert message == "Score must be 'up' or 'down'"

    @patch("app.services.feedback_service.engine")
    def test_submit_feedback_query_not_found(self, mock_engine):
        """Test feedback submission when query doesn't exist"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock table info query
        mock_conn.execute.return_value.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Mock query existence check - query doesn't exist
        mock_conn.execute.return_value.fetchone.return_value = None

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )

        assert success is False
        assert message == "Query not found"

    @patch("app.services.feedback_service.FeedbackService._query_exists")
    @patch("app.services.feedback_service.FeedbackService._feedback_exists")
    def test_submit_feedback_already_exists(
        self, mock_feedback_exists, mock_query_exists
    ):
        """Test feedback submission when feedback already exists"""
        # Mock the helper methods directly
        mock_query_exists.return_value = True  # Query exists
        mock_feedback_exists.return_value = True  # Feedback exists

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )

        assert success is False
        assert message == "Feedback already submitted for this query"

    @patch("app.services.feedback_service.FeedbackService._query_exists")
    @patch("app.services.feedback_service.FeedbackService._feedback_exists")
    def test_submit_feedback_database_error(
        self, mock_feedback_exists, mock_query_exists
    ):
        """Test feedback submission with database error"""
        # Mock the helper methods directly
        mock_query_exists.return_value = True  # Query exists
        mock_feedback_exists.return_value = False  # Feedback doesn't exist

        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (score column exists)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Set up side effects for execute calls - error on insert
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            Exception("Database connection failed"),  # Insert fails
        ]

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )

        assert success is False
        assert message == "Unexpected error occurred"

    @patch("app.services.feedback_service.FeedbackService._query_exists")
    @patch("app.services.feedback_service.FeedbackService._feedback_exists")
    def test_submit_feedback_without_score_column(
        self, mock_feedback_exists, mock_query_exists
    ):
        """Test feedback submission when score column doesn't exist"""
        # Mock the helper methods directly
        mock_query_exists.return_value = True  # Query exists
        mock_feedback_exists.return_value = False  # Feedback doesn't exist

        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (no score column)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "feedback", "TEXT", 0, None, 0),
            (4, "comment", "TEXT", 0, None, 0),
            (5, "created_at", "DATETIME", 0, None, 0),
        ]

        mock_insert_result = MagicMock()
        mock_insert_result.rowcount = 1

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_insert_result,  # Insert feedback
        ]

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )

        assert success is True
        assert message == "Feedback submitted successfully"

    def test_get_feedback_stats(self):
        """Test getting feedback statistics"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (score column exists)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Mock stats query result
        mock_row = MagicMock()
        mock_row.score = "up"
        mock_row.count = 5
        mock_row2 = MagicMock()
        mock_row2.score = "down"
        mock_row2.count = 2

        mock_stats_result = MagicMock()
        mock_stats_result.fetchall.return_value = [mock_row, mock_row2]

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_stats_result,  # Stats query
        ]

        stats = self.feedback_service.get_feedback_stats(self.test_query_id)

        assert stats["up"] == 5
        assert stats["down"] == 2

    def test_get_feedback_stats_no_score_column(self):
        """Test getting feedback statistics without score column"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (no score column)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "feedback", "TEXT", 0, None, 0),
        ]

        # Mock stats query result
        mock_row = MagicMock()
        mock_row.score = "up"
        mock_row.count = 3

        mock_stats_result = MagicMock()
        mock_stats_result.fetchall.return_value = [mock_row]

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_stats_result,  # Stats query
        ]

        stats = self.feedback_service.get_feedback_stats(self.test_query_id)

        assert stats["up"] == 3
        assert stats["down"] == 0

    def test_get_feedback_stats_database_error(self):
        """Test getting feedback statistics with database error"""
        # Mock the engine on the service instance to raise error on first connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.side_effect = Exception("Database error")
        self.feedback_service.engine = mock_engine

        stats = self.feedback_service.get_feedback_stats(self.test_query_id)

        assert stats["up"] == 0
        assert stats["down"] == 0

    def test_get_user_feedback(self):
        """Test getting user feedback history"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (score column exists)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Mock user feedback query result
        mock_row = MagicMock()
        mock_row.id = "feedback-123"
        mock_row.query_id = "query-456"
        mock_row.score = "up"
        mock_row.comment = "Great answer!"
        mock_row.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_row.question = "What is AI?"
        mock_row.response = "AI is artificial intelligence"

        mock_user_feedback_result = MagicMock()
        mock_user_feedback_result.fetchall.return_value = [mock_row]

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_user_feedback_result,  # User feedback query
        ]

        feedback_list = self.feedback_service.get_user_feedback(
            self.test_user_id, limit=10
        )

        assert len(feedback_list) == 1
        assert feedback_list[0]["id"] == "feedback-123"
        assert feedback_list[0]["query_id"] == "query-456"
        assert feedback_list[0]["score"] == "up"
        assert feedback_list[0]["comment"] == "Great answer!"
        assert feedback_list[0]["question"] == "What is AI?"
        assert feedback_list[0]["response"] == "AI is artificial intelligence"

    def test_get_feedback_summary(self):
        """Test getting feedback summary"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query (score column exists)
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Mock summary query result
        mock_row = MagicMock()
        mock_row.total_feedback = 10
        mock_row.up_votes = 7
        mock_row.down_votes = 3
        mock_row.unique_users = 5
        mock_row.unique_messages = 8

        mock_summary_result = MagicMock()
        mock_summary_result.fetchone.return_value = mock_row

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_summary_result,  # Summary query
        ]

        summary = self.feedback_service.get_feedback_summary(days=7)

        assert summary["total_feedback"] == 10
        assert summary["up_votes"] == 7
        assert summary["down_votes"] == 3
        assert summary["unique_users"] == 5
        assert summary["unique_messages"] == 8
        assert summary["satisfaction_rate"] == 70.0  # 7/10 * 100

    def test_get_feedback_summary_no_data(self):
        """Test getting feedback summary with no data"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock table info query
        mock_table_info_result = MagicMock()
        mock_table_info_result.fetchall.return_value = [
            (0, "id", "TEXT", 0, None, 1),
            (1, "query_id", "TEXT", 0, None, 0),
            (2, "user_id", "TEXT", 0, None, 0),
            (3, "score", "TEXT", 0, None, 0),
        ]

        # Mock summary query result - no data
        mock_summary_result = MagicMock()
        mock_summary_result.fetchone.return_value = None

        # Set up side effects for execute calls
        mock_conn.execute.side_effect = [
            mock_table_info_result,  # PRAGMA table_info
            mock_summary_result,  # Summary query
        ]

        summary = self.feedback_service.get_feedback_summary(days=7)

        assert summary["total_feedback"] == 0
        assert summary["up_votes"] == 0
        assert summary["down_votes"] == 0
        assert summary["unique_users"] == 0
        assert summary["unique_messages"] == 0
        assert summary["satisfaction_rate"] == 0

    def test_query_exists(self):
        """Test _query_exists method"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock query exists
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_conn.execute.return_value = mock_result

        exists = self.feedback_service._query_exists(self.test_query_id)

        assert exists is True
        mock_conn.execute.assert_called_once()

    @patch("app.services.feedback_service.engine")
    def test_query_not_exists(self, mock_engine):
        """Test _query_exists method when query doesn't exist"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock query doesn't exist
        mock_conn.execute.return_value.fetchone.return_value = None

        exists = self.feedback_service._query_exists(self.test_query_id)

        assert exists is False

    def test_feedback_exists(self):
        """Test _feedback_exists method"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock feedback exists
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_conn.execute.return_value = mock_result

        exists = self.feedback_service._feedback_exists(
            self.test_query_id, self.test_user_id
        )

        assert exists is True
        mock_conn.execute.assert_called_once()

    def test_feedback_not_exists(self):
        """Test _feedback_exists method when feedback doesn't exist"""
        # Mock the engine on the service instance
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        self.feedback_service.engine = mock_engine

        # Mock feedback doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        exists = self.feedback_service._feedback_exists(
            self.test_query_id, self.test_user_id
        )

        assert exists is False


class TestFeedbackServiceIntegration:
    """Integration tests for Feedback service"""

    def test_full_feedback_workflow(self):
        """Test complete feedback workflow"""
        # This would be an integration test that actually uses the database
        # For now, we'll test the service methods work together
        feedback_service = FeedbackService()

        # Test that the service can be instantiated
        assert feedback_service is not None
        assert feedback_service.engine is not None

    def test_feedback_service_singleton(self):
        """Test that feedback service can be used as singleton"""
        from app.services.feedback_service import feedback_service

        # Test that the global instance exists
        assert feedback_service is not None
        assert isinstance(feedback_service, FeedbackService)


if __name__ == "__main__":
    pytest.main([__file__])
