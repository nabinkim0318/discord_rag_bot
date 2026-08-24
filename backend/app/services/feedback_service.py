"""
Feedback service for handling user feedback on RAG responses
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import case, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.logging import logger
from app.core.metrics import feedback_satisfaction_rate, feedback_submissions
from app.db.session import engine as default_engine
from app.models.feedback import Feedback
from app.models.query import Query


def _utc_now() -> datetime:
    """Naive UTC timestamp matching the DateTime column contract."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FeedbackService:
    """Service for managing user feedback on RAG responses"""

    def __init__(self, engine: Optional[Engine] = None):
        """Initialize feedback service with database connection"""
        self.engine = engine or default_engine

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
            if score not in ["up", "down"]:
                return False, "Score must be 'up' or 'down'"

            with Session(self.engine) as session:
                if not self._query_exists(query_id, session):
                    return False, "Query not found"

                if self._feedback_exists(query_id, user_id, session):
                    return False, "Feedback already submitted for this query"

                session.add(
                    Feedback(
                        id=uuid4(),
                        query_id=query_id,
                        user_id=user_id,
                        score=score,
                        comment=comment,
                        created_at=_utc_now(),
                    )
                )
                session.commit()

                total = session.exec(select(func.count()).select_from(Feedback)).one()
                up_ct = session.exec(
                    select(func.count())
                    .select_from(Feedback)
                    .where(Feedback.score == "up")
                ).one()

            logger.info(f"Feedback submitted for query {query_id}")

            feedback_submissions.labels(score=score).inc()
            try:
                rate = (up_ct / total) if total else 0.0
                feedback_satisfaction_rate.set(rate)
            except Exception:
                pass

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
            statement = (
                select(Feedback.score, func.count())
                .where(Feedback.query_id == query_id)
                .group_by(Feedback.score)
            )
            with Session(self.engine) as session:
                rows = session.exec(statement).all()

            stats = {"up": 0, "down": 0}
            for score, count in rows:
                if score in stats:
                    stats[score] = int(count)
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
            statement = (
                select(Feedback, Query)
                .join(Query, Feedback.query_id == Query.id)
                .where(Feedback.user_id == user_id)
                .order_by(Feedback.created_at.desc())
                .limit(limit)
            )
            with Session(self.engine) as session:
                rows = session.exec(statement).all()

            feedback_list = []
            for feedback, query in rows:
                created_at = feedback.created_at
                if hasattr(created_at, "isoformat"):
                    created_at_str = created_at.isoformat()
                else:
                    created_at_str = str(created_at)

                feedback_list.append(
                    {
                        "id": str(feedback.id),
                        "query_id": str(feedback.query_id),
                        "score": feedback.score,
                        "comment": feedback.comment,
                        "created_at": created_at_str,
                        "question": query.query,
                        "response": query.answer,
                    }
                )

            return feedback_list

        except SQLAlchemyError as e:
            logger.error(f"Database error getting user feedback: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting user feedback: {e}")
            return []

    def _query_exists(self, query_id: str, session: Optional[Session] = None) -> bool:
        """Check if a query exists in the database"""
        statement = select(Query.id).where(Query.id == query_id)
        if session is not None:
            return session.exec(statement).first() is not None
        with Session(self.engine) as owned_session:
            return owned_session.exec(statement).first() is not None

    def _feedback_exists(
        self,
        query_id: str,
        user_id: str,
        session: Optional[Session] = None,
    ) -> bool:
        """Check if feedback already exists for this query from this user"""
        statement = select(Feedback.id).where(
            Feedback.query_id == query_id,
            Feedback.user_id == user_id,
        )
        if session is not None:
            return session.exec(statement).first() is not None
        with Session(self.engine) as owned_session:
            return owned_session.exec(statement).first() is not None

    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get feedback summary for the last N days

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with summary statistics
        """
        empty = {
            "total_feedback": 0,
            "up_votes": 0,
            "down_votes": 0,
            "unique_users": 0,
            "unique_messages": 0,
            "satisfaction_rate": 0,
        }
        try:
            cutoff = _utc_now() - timedelta(days=days)
            statement = select(
                func.count().label("total_feedback"),
                func.coalesce(
                    func.sum(case((Feedback.score == "up", 1), else_=0)), 0
                ).label("up_votes"),
                func.coalesce(
                    func.sum(case((Feedback.score == "down", 1), else_=0)), 0
                ).label("down_votes"),
                func.count(func.distinct(Feedback.user_id)).label("unique_users"),
                func.count(func.distinct(Feedback.query_id)).label("unique_messages"),
            ).where(Feedback.created_at >= cutoff)

            with Session(self.engine) as session:
                result = session.exec(statement).one()

            if not result:
                return empty

            total = int(result.total_feedback or 0)
            up_votes = int(result.up_votes or 0)
            down_votes = int(result.down_votes or 0)

            return {
                "total_feedback": total,
                "up_votes": up_votes,
                "down_votes": down_votes,
                "unique_users": int(result.unique_users or 0),
                "unique_messages": int(result.unique_messages or 0),
                "satisfaction_rate": (up_votes / total * 100) if total > 0 else 0,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting feedback summary: {e}")
            return empty
        except Exception as e:
            logger.error(f"Unexpected error getting feedback summary: {e}")
            return empty


# Global instance
feedback_service = FeedbackService()
