"""
Feedback service for handling user feedback on RAG responses
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import logger
from app.core.metrics import feedback_submissions
from app.db.session import engine


class FeedbackService:
    """Service for managing user feedback on RAG responses"""

    def __init__(self):
        """Initialize feedback service with database connection"""
        self.engine = engine

    def submit_feedback(
        self, query_id: str, user_id: str, score: str, comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Submit user feedback for a RAG response

        Args:
            query_id: UUID of the original query
            user_id: Discord user ID
            score: 'up' or 'down'
            comment: Optional comment from user

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate score
            if score not in ["up", "down"]:
                return False, "Score must be 'up' or 'down'"

            # Check if query exists
            if not self._query_exists(query_id):
                return False, "Query not found"

            # Check if feedback already exists for this query from this user
            if self._feedback_exists(query_id, user_id):
                return False, "Feedback already submitted for this query"

            # Insert feedback
            feedback_id = str(uuid.uuid4())
            # Check if score column exists, otherwise use feedback column
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(feedback)"))
                columns = [col[1] for col in result.fetchall()]
                has_score_column = "score" in columns

            if has_score_column:
                # Use both score and feedback columns for compatibility
                query = text(
                    """
                    INSERT INTO feedback (id, query_id, user_id,
                    score, feedback, comment, created_at)
                    VALUES (:id, :query_id, :user_id, :score, :score,
                    :comment, :created_at)
                """
                )
            else:
                query = text(
                    """
                    INSERT INTO feedback (id, query_id, user_id,
                    feedback, comment, created_at)
                    VALUES (:id, :query_id, :user_id, :score,
                    :comment, :created_at)
                """
                )

            with self.engine.connect() as conn:
                conn.execute(
                    query,
                    {
                        "id": feedback_id,
                        "query_id": query_id,
                        "user_id": user_id,
                        "score": score,
                        "comment": comment,
                        "created_at": datetime.utcnow(),
                    },
                )
                conn.commit()

            logger.info(f"Feedback submitted: {feedback_id} for query {query_id}")

            # Record metrics
            feedback_submissions.labels(score=score).inc()

            return True, "Feedback submitted successfully"

        except SQLAlchemyError as e:
            logger.error(f"Database error submitting feedback: {e}")
            return False, "Database error occurred"
        except Exception as e:
            logger.error(f"Unexpected error submitting feedback: {e}")
            return False, "Unexpected error occurred"

    def get_feedback_stats(self, query_id: str) -> Dict[str, int]:
        """
        Get feedback statistics for a query

        Args:
            query_id: UUID of the query

        Returns:
            Dictionary with up/down counts
        """
        try:
            # Check if score column exists, otherwise use feedback column
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(feedback)"))
                columns = [col[1] for col in result.fetchall()]
                has_score_column = "score" in columns

            if has_score_column:
                query = text(
                    """
                    SELECT score, COUNT(*) as count
                    FROM feedback
                    WHERE query_id = :query_id
                    GROUP BY score
                """
                )
            else:
                query = text(
                    """
                    SELECT feedback as score, COUNT(*) as count
                    FROM feedback
                    WHERE query_id = :query_id
                    GROUP BY feedback
                """
                )

            with self.engine.connect() as conn:
                result = conn.execute(query, {"query_id": query_id}).fetchall()

            stats = {"up": 0, "down": 0}
            for row in result:
                stats[row.score] = row.count

            return stats

        except SQLAlchemyError as e:
            logger.error(f"Database error getting feedback stats: {e}")
            return {"up": 0, "down": 0}
        except Exception as e:
            logger.error(f"Unexpected error getting feedback stats: {e}")
            return {"up": 0, "down": 0}

    def get_user_feedback(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get feedback history for a user

        Args:
            user_id: Discord user ID
            limit: Maximum number of feedback records to return

        Returns:
            List of feedback records
        """
        try:
            # Check if score column exists, otherwise use feedback column
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(feedback)"))
                columns = [col[1] for col in result.fetchall()]
                has_score_column = "score" in columns

            if has_score_column:
                query = text(
                    """
                    SELECT f.id, f.query_id, f.score, f.comment, f.created_at,
                           q.query AS question, q.answer AS response
                    FROM feedback f
                    JOIN queries q ON f.query_id = q.id
                    WHERE f.user_id = :user_id
                    ORDER BY f.created_at DESC
                    LIMIT :limit
                """
                )
            else:
                query = text(
                    """
                    SELECT f.id, f.query_id, f.feedback as score,
                            f.comment, f.created_at,
                           q.query AS question, q.answer AS response
                    FROM feedback f
                    JOIN queries q ON f.query_id = q.id
                    WHERE f.user_id = :user_id
                    ORDER BY f.created_at DESC
                    LIMIT :limit
                """
                )

            with self.engine.connect() as conn:
                result = conn.execute(
                    query, {"user_id": user_id, "limit": limit}
                ).fetchall()

            feedback_list = []
            for row in result:
                # Handle created_at field safely
                created_at = row.created_at
                if hasattr(created_at, "isoformat"):
                    created_at_str = created_at.isoformat()
                else:
                    created_at_str = str(created_at)

                feedback_list.append(
                    {
                        "id": str(row.id),
                        "query_id": str(row.query_id),
                        "score": row.score,
                        "comment": row.comment,
                        "created_at": created_at_str,
                        "question": row.question,
                        "response": row.response,
                    }
                )

            return feedback_list

        except SQLAlchemyError as e:
            logger.error(f"Database error getting user feedback: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting user feedback: {e}")
            return []

    def _query_exists(self, query_id: str) -> bool:
        """Check if a query exists in the database"""
        try:
            query = text("SELECT 1 FROM queries WHERE id = :query_id")
            with self.engine.connect() as conn:
                result = conn.execute(query, {"query_id": query_id}).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking query existence: {e}")
            return False

    def _feedback_exists(self, query_id: str, user_id: str) -> bool:
        """Check if feedback already exists for this query from this user"""
        try:
            query = text(
                """
                SELECT 1 FROM feedback
                WHERE query_id = :query_id AND user_id = :user_id
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(
                    query, {"query_id": query_id, "user_id": user_id}
                ).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking feedback existence: {e}")
            return False

    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get feedback summary for the last N days

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Check if score column exists, otherwise use feedback column
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(feedback)"))
                columns = [col[1] for col in result.fetchall()]
                has_score_column = "score" in columns

            if has_score_column:
                query = text(
                    """
                    SELECT
                        COUNT(*) as total_feedback,
                        SUM(CASE WHEN score = 'up' THEN 1 ELSE 0 END) as up_votes,
                        SUM(CASE WHEN score = 'down' THEN 1 ELSE 0 END) as down_votes,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT query_id) as unique_messages
                    FROM feedback
                    WHERE created_at >= datetime('now', '-{} days')
                """.format(days)
                )
            else:
                query = text(
                    """
                    SELECT
                        COUNT(*) as total_feedback,
                        SUM(CASE WHEN feedback = 'up' THEN 1 ELSE 0 END)
                            as up_votes,
                        SUM(CASE WHEN feedback = 'down' THEN 1 ELSE 0 END)
                            as down_votes,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT query_id) as unique_messages
                    FROM feedback
                    WHERE created_at >= datetime('now', '-{} days')
                """.format(days)
                )

            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()

            if result:
                total = result.total_feedback or 0
                up_votes = result.up_votes or 0
                down_votes = result.down_votes or 0

                return {
                    "total_feedback": total,
                    "up_votes": up_votes,
                    "down_votes": down_votes,
                    "unique_users": result.unique_users or 0,
                    "unique_messages": result.unique_messages or 0,
                    "satisfaction_rate": (up_votes / total * 100) if total > 0 else 0,
                }
            else:
                return {
                    "total_feedback": 0,
                    "up_votes": 0,
                    "down_votes": 0,
                    "unique_users": 0,
                    "unique_messages": 0,
                    "satisfaction_rate": 0,
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting feedback summary: {e}")
            return {
                "total_feedback": 0,
                "up_votes": 0,
                "down_votes": 0,
                "unique_users": 0,
                "unique_messages": 0,
                "satisfaction_rate": 0,
            }
        except Exception as e:
            logger.error(f"Unexpected error getting feedback summary: {e}")
            return {
                "total_feedback": 0,
                "up_votes": 0,
                "down_votes": 0,
                "unique_users": 0,
                "unique_messages": 0,
                "satisfaction_rate": 0,
            }


# Global instance
feedback_service = FeedbackService()
