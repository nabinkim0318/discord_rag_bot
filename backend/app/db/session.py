# app/db/session.py
import os
import time
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, create_engine

from app.core.logging import log_database_operation, logger

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite3")
engine = create_engine(
    DATABASE_URL,
    echo=False,  # SQL query logging (only True for development)
    pool_pre_ping=True,  # Check connection status
    pool_recycle=300,  # Recreate connection every 5 minutes
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    """
    Database session dependency
    Used in FastAPI Depends
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Manage database session with context manager
    Used when directly using the session
    """
    start_time = time.time()
    session = Session(engine)

    try:
        log_database_operation("SESSION_START", "database", True)
        yield session
        session.commit()
        log_database_operation(
            "SESSION_COMMIT", "database", True, time.time() - start_time
        )

    except Exception as e:
        session.rollback()
        log_database_operation(
            "SESSION_ROLLBACK", "database", False, time.time() - start_time
        )
        logger.error(f"Database operation failed: {str(e)}")
        raise

    finally:
        session.close()
        log_database_operation(
            "SESSION_CLOSE", "database", True, time.time() - start_time
        )
