"""Helpers for isolated database tests."""

from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.db.session import configure_sqlite_engine
from app.models import feedback as _feedback_model  # noqa: F401
from app.models import query as _query_model  # noqa: F401

EXPECTED_TABLES = {"queries", "feedback"}
EXPECTED_QUERY_COLUMNS = {
    "id": False,
    "user_id": True,
    "query": False,
    "answer": False,
    "context": True,
    "created_at": False,
}
EXPECTED_FEEDBACK_COLUMNS = {
    "id": False,
    "query_id": False,
    "user_id": False,
    "score": False,
    "comment": True,
    "created_at": False,
}


def create_memory_engine() -> Engine:
    """Create an isolated in-memory SQLite engine with FK enforcement."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_sqlite_engine(engine)
    SQLModel.metadata.create_all(engine)
    return engine


def schema_snapshot(engine: Engine) -> dict:
    """Capture tables, columns, foreign keys, and indexes."""
    inspector = inspect(engine)
    tables = {}
    for name in inspector.get_table_names():
        if name == "alembic_version":
            continue
        tables[name] = {
            "columns": {
                col["name"]: {"nullable": col["nullable"]}
                for col in inspector.get_columns(name)
            },
            "foreign_keys": [
                {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
                for fk in inspector.get_foreign_keys(name)
            ],
            "indexes": {
                idx["name"]: {
                    "column_names": idx["column_names"],
                    "unique": bool(idx["unique"]),
                }
                for idx in inspector.get_indexes(name)
            },
        }
    return tables


def apply_alembic(url: str) -> None:
    """Upgrade an empty database URL to Alembic head."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["sqlalchemy_url"] = url
    command.upgrade(cfg, "head")
