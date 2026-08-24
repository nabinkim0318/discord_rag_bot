#!/usr/bin/env python3
"""
Database initialization script
- Applies Alembic migrations (runtime schema authority)
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.logging import logger  # noqa: E402
from app.db.schema import apply_schema  # noqa: E402
from app.db.session import engine  # noqa: E402


def init_database():
    """Initialize database tables using Alembic."""
    try:
        logger.info("Applying Alembic migrations...")
        apply_schema(engine)
        logger.info("✅ Database schema is up to date")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to apply database schema: {e}")
        return False


def init_alembic():
    """Confirm Alembic is already configured for this project."""
    try:
        backend_dir = Path(__file__).parent.parent / "backend"
        versions = backend_dir / "alembic" / "versions"
        if versions.exists():
            logger.info("✅ Alembic already initialized")
            return True

        logger.error("❌ Alembic versions directory is missing")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to verify Alembic: {e}")
        return False


def main():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization...")

    if not init_database():
        sys.exit(1)

    if os.getenv("INIT_ALEMBIC", "false").lower() == "true":
        if not init_alembic():
            logger.warning(
                "⚠️ Alembic verification failed, but migrations were applied"
            )

    logger.info("🎉 Database initialization completed successfully!")


if __name__ == "__main__":
    main()
