"""
Feedback service for handling user feedback on RAG responses
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import logger


class FeedbackService:
    """Service for managing user feedback on RAG responses"""

    def __init__(self):
        """Initialize feedback service with database connection"""
        self.engine = create_engine(settings.DATABASE_URL)

    def submit_feedback(
        self, message_id: str, user_id: str, score: str, comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Submit user feedback for a RAG response

        Args:
            message_id: UUID of the original message
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

            # Check if message exists
            if not self._message_exists(message_id):
                return False, "Message not found"

            # Check if feedback already exists for this message from this user
            if self._feedback_exists(message_id, user_id):
                return False, "Feedback already submitted for this message"

            # Insert feedback
            feedback_id = str(uuid.uuid4())
            query = text(
                """
                INSERT INTO feedback (id, message_id, user_id,
                score, comment, created_at)
                VALUES (:id, :message_id, :user_id, :score,
                :comment, :created_at)
            """
            )

            with self.engine.connect() as conn:
                conn.execute(
                    query,
                    {
                        "id": feedback_id,
                        "message_id": message_id,
                        "user_id": user_id,
                        "score": score,
                        "comment": comment,
                        "created_at": datetime.utcnow(),
                    },
                )
                conn.commit()

            logger.info(f"Feedback submitted: {feedback_id} for message {message_id}")
            return True, "Feedback submitted successfully"

        except SQLAlchemyError as e:
            logger.error(f"Database error submitting feedback: {e}")
            return False, "Database error occurred"
        except Exception as e:
            logger.error(f"Unexpected error submitting feedback: {e}")
            return False, "Unexpected error occurred"

    def get_feedback_stats(self, message_id: str) -> Dict[str, int]:
        """
        Get feedback statistics for a message

        Args:
            message_id: UUID of the message

        Returns:
            Dictionary with up/down counts
        """
        try:
            query = text(
                """
                SELECT score, COUNT(*) as count
                FROM feedback
                WHERE message_id = :message_id
                GROUP BY score
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(query, {"message_id": message_id}).fetchall()

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
            query = text(
                """
                SELECT f.id, f.message_id, f.score, f.comment, f.created_at,
                       um.question, um.response
                FROM feedback f
                JOIN user_messages um ON f.message_id = um.id
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
                feedback_list.append(
                    {
                        "id": str(row.id),
                        "message_id": str(row.message_id),
                        "score": row.score,
                        "comment": row.comment,
                        "created_at": row.created_at.isoformat(),
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

    def _message_exists(self, message_id: str) -> bool:
        """Check if a message exists in the database"""
        try:
            query = text("SELECT 1 FROM user_messages WHERE id = :message_id")
            with self.engine.connect() as conn:
                result = conn.execute(query, {"message_id": message_id}).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking message existence: {e}")
            return False

    def _feedback_exists(self, message_id: str, user_id: str) -> bool:
        """Check if feedback already exists for this message from this user"""
        try:
            query = text(
                """
                SELECT 1 FROM feedback
                WHERE message_id = :message_id AND user_id = :user_id
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(
                    query, {"message_id": message_id, "user_id": user_id}
                ).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking feedback existence: {e}")
            return False

    def get_feedback_summary(self, days: int = 7) -> Dict[str, any]:
        """
        Get feedback summary for the last N days

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with summary statistics
        """
        try:
            query = text(
                """
                SELECT
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN score = 'up' THEN 1 ELSE 0 END) as up_votes,
                    SUM(CASE WHEN score = 'down' THEN 1 ELSE 0 END) as down_votes,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT message_id) as unique_messages
                FROM feedback
                WHERE created_at >= datetime('now', '-{} days')
            """.format(
                    days
                )
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
