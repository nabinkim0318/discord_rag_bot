#!/usr/bin/env python3
"""
Database initialization script
- Creates tables using SQLModel
- Optionally initializes Alembic for future migrations
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlmodel import SQLModel  # noqa: E402

from app.core.logging import logger  # noqa: E402
from app.db.session import engine  # noqa: E402


def init_database():
    """Initialize database tables using SQLModel"""
    try:
        logger.info("Initializing database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False


def init_alembic():
    """Initialize Alembic for future migrations"""
    try:
        import subprocess
        from pathlib import Path

        backend_dir = Path(__file__).parent.parent / "backend"
        os.chdir(backend_dir)

        # Check if alembic is already initialized
        if (backend_dir / "alembic" / "versions").exists():
            logger.info("✅ Alembic already initialized")
            return True

        # Initialize alembic
        logger.info("Initializing Alembic...")
        result = subprocess.run(
            ["alembic", "init", "alembic"], capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("✅ Alembic initialized successfully")
            return True
        else:
            logger.error(f"❌ Failed to initialize Alembic: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to initialize Alembic: {e}")
        return False


def main():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization...")

    # Initialize database tables
    if not init_database():
        sys.exit(1)

    # Optionally initialize Alembic
    if os.getenv("INIT_ALEMBIC", "false").lower() == "true":
        if not init_alembic():
            logger.warning(
                "⚠️ Alembic initialization failed, but database tables were created"
            )

    logger.info("🎉 Database initialization completed successfully!")


if __name__ == "__main__":
    main()
