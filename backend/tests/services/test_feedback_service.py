"""
Tests for Feedback service functionality
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from db_test_utils import create_memory_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session

from app.models.feedback import Feedback
from app.models.query import Query
from app.services.feedback_service import FeedbackService


class TestFeedbackService:
    """Test Feedback service against the declared schema."""

    def setup_method(self):
        self.engine = create_memory_engine()
        self.feedback_service = FeedbackService(self.engine)
        self.test_user_id = "user-456"
        self.test_score = "up"
        self.test_comment = "This was helpful!"
        with Session(self.engine) as session:
            query = Query(
                user_id=self.test_user_id,
                query="What is AI?",
                answer="AI is artificial intelligence",
                context={},
            )
            session.add(query)
            session.commit()
            session.refresh(query)
            self.test_query_id = query.id

    def teardown_method(self):
        self.engine.dispose()

    def test_submit_feedback_success(self):
        success, message = self.feedback_service.submit_feedback(
            self.test_query_id,
            self.test_user_id,
            self.test_score,
            self.test_comment,
        )

        assert success is True
        assert message == "Feedback submitted successfully"

        history = self.feedback_service.get_user_feedback(self.test_user_id)
        assert len(history) == 1
        assert history[0]["score"] == "up"
        assert history[0]["comment"] == self.test_comment
        assert history[0]["question"] == "What is AI?"

    def test_submit_feedback_invalid_score(self):
        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, "invalid_score", self.test_comment
        )

        assert success is False
        assert message == "Score must be 'up' or 'down'"

    def test_submit_feedback_query_not_found(self):
        success, message = self.feedback_service.submit_feedback(
            "missing-query", self.test_user_id, self.test_score, self.test_comment
        )

        assert success is False
        assert message == "Query not found"

    def test_submit_feedback_already_exists(self):
        first, _ = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, self.test_score, self.test_comment
        )
        assert first is True

        success, message = self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, "down", "again"
        )

        assert success is False
        assert message == "Feedback already submitted for this query"

    def test_submit_feedback_database_error(self):
        mock_session = MagicMock()
        mock_session.exec.side_effect = SQLAlchemyError("connection failed")

        with patch(
            "app.services.feedback_service.Session",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=mock_session),
                __exit__=MagicMock(return_value=False),
            ),
        ):
            success, message = self.feedback_service.submit_feedback(
                self.test_query_id,
                self.test_user_id,
                self.test_score,
                self.test_comment,
            )

        assert success is False
        assert message == "Database error occurred"

    def test_get_feedback_stats(self):
        self.feedback_service.submit_feedback(self.test_query_id, "user-a", "up", None)
        self.feedback_service.submit_feedback(self.test_query_id, "user-b", "up", None)
        self.feedback_service.submit_feedback(
            self.test_query_id, "user-c", "down", None
        )

        stats = self.feedback_service.get_feedback_stats(self.test_query_id)

        assert stats["up"] == 2
        assert stats["down"] == 1

    def test_get_feedback_stats_empty(self):
        stats = self.feedback_service.get_feedback_stats(self.test_query_id)
        assert stats == {"up": 0, "down": 0}

    def test_get_user_feedback(self):
        self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, "up", "Great answer!"
        )

        feedback_list = self.feedback_service.get_user_feedback(
            self.test_user_id, limit=10
        )

        assert len(feedback_list) == 1
        assert feedback_list[0]["query_id"] == self.test_query_id
        assert feedback_list[0]["score"] == "up"
        assert feedback_list[0]["comment"] == "Great answer!"
        assert feedback_list[0]["question"] == "What is AI?"
        assert feedback_list[0]["response"] == "AI is artificial intelligence"

    def test_get_feedback_summary(self):
        self.feedback_service.submit_feedback(self.test_query_id, "user-a", "up", None)
        self.feedback_service.submit_feedback(
            self.test_query_id, "user-b", "down", None
        )

        with Session(self.engine) as session:
            extra_query = Query(
                user_id="user-old",
                query="old",
                answer="old answer",
                context={},
            )
            session.add(extra_query)
            session.commit()
            session.refresh(extra_query)
            session.add(
                Feedback(
                    query_id=extra_query.id,
                    user_id="user-old",
                    score="up",
                    created_at=datetime.utcnow() - timedelta(days=30),
                )
            )
            session.commit()

        summary = self.feedback_service.get_feedback_summary(days=7)

        assert summary["total_feedback"] == 2
        assert summary["up_votes"] == 1
        assert summary["down_votes"] == 1
        assert summary["unique_users"] == 2
        assert summary["unique_messages"] == 1
        assert summary["satisfaction_rate"] == 50.0

    def test_get_feedback_summary_no_data(self):
        summary = self.feedback_service.get_feedback_summary(days=7)

        assert summary["total_feedback"] == 0
        assert summary["up_votes"] == 0
        assert summary["down_votes"] == 0
        assert summary["unique_users"] == 0
        assert summary["unique_messages"] == 0
        assert summary["satisfaction_rate"] == 0

    def test_query_exists(self):
        assert self.feedback_service._query_exists(self.test_query_id) is True

    def test_query_not_exists(self):
        assert self.feedback_service._query_exists("missing-query") is False

    def test_feedback_exists(self):
        self.feedback_service.submit_feedback(
            self.test_query_id, self.test_user_id, "up", None
        )
        assert (
            self.feedback_service._feedback_exists(
                self.test_query_id, self.test_user_id
            )
            is True
        )

    def test_feedback_not_exists(self):
        assert (
            self.feedback_service._feedback_exists(
                self.test_query_id, self.test_user_id
            )
            is False
        )

    def test_foreign_key_rejects_orphan_feedback(self):
        with Session(self.engine) as session:
            session.add(
                Feedback(
                    query_id="does-not-exist",
                    user_id="user-x",
                    score="up",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()


class TestFeedbackServiceIntegration:
    """Integration tests for Feedback service"""

    def test_full_feedback_workflow(self):
        engine = create_memory_engine()
        try:
            feedback_service = FeedbackService(engine)
            assert feedback_service is not None
            assert feedback_service.engine is engine
        finally:
            engine.dispose()

    def test_feedback_service_singleton(self):
        from app.services.feedback_service import feedback_service

        assert feedback_service is not None
        assert isinstance(feedback_service, FeedbackService)


if __name__ == "__main__":
    pytest.main([__file__])
