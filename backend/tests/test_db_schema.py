"""Schema ownership and portability tests."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from db_test_utils import (
    EXPECTED_FEEDBACK_COLUMNS,
    EXPECTED_QUERY_COLUMNS,
    EXPECTED_TABLES,
    apply_alembic,
    create_memory_engine,
    schema_snapshot,
)
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel, select

from app.db.schema import apply_schema
from app.models.feedback import Feedback
from app.models.query import Query
from app.services.feedback_service import FeedbackService


def _assert_intended_schema(snapshot: dict) -> None:
    assert set(snapshot) == EXPECTED_TABLES
    assert set(snapshot["queries"]["columns"]) == set(EXPECTED_QUERY_COLUMNS)
    assert set(snapshot["feedback"]["columns"]) == set(EXPECTED_FEEDBACK_COLUMNS)

    for name, nullable in EXPECTED_QUERY_COLUMNS.items():
        assert snapshot["queries"]["columns"][name]["nullable"] is nullable
    for name, nullable in EXPECTED_FEEDBACK_COLUMNS.items():
        assert snapshot["feedback"]["columns"][name]["nullable"] is nullable

    assert "query" not in snapshot
    assert "score" in snapshot["feedback"]["columns"]
    assert "feedback" not in snapshot["feedback"]["columns"]

    fks = snapshot["feedback"]["foreign_keys"]
    assert any(
        fk["constrained_columns"] == ["query_id"]
        and fk["referred_table"] == "queries"
        and fk["referred_columns"] == ["id"]
        for fk in fks
    )

    index_names = set(snapshot["queries"]["indexes"])
    assert "ix_queries_id" in index_names
    assert "ix_queries_user_id" in index_names


def test_create_all_matches_intended_sqlmodel_schema():
    engine = create_memory_engine()
    try:
        _assert_intended_schema(schema_snapshot(engine))
    finally:
        engine.dispose()


def test_fresh_alembic_upgrade_matches_intended_schema():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    try:
        url = f"sqlite:///{path}"
        apply_alembic(url)
        engine = create_engine(url)
        snapshot = schema_snapshot(engine)
        _assert_intended_schema(snapshot)

        inspector = inspect(engine)
        assert "alembic_version" in inspector.get_table_names()
        with engine.connect() as conn:
            version = conn.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar()
        assert version == "b7e2c4a91f03"
        engine.dispose()
    finally:
        Path(path).unlink(missing_ok=True)


def test_alembic_schema_matches_sqlmodel_create_all():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    try:
        alembic_engine = create_engine(f"sqlite:///{path}")
        apply_schema(alembic_engine)
        alembic_snapshot = schema_snapshot(alembic_engine)
        alembic_engine.dispose()

        model_engine = create_memory_engine()
        model_snapshot = schema_snapshot(model_engine)
        model_engine.dispose()

        assert alembic_snapshot == model_snapshot
    finally:
        Path(path).unlink(missing_ok=True)


def test_query_feedback_foreign_key_is_enforced():
    engine = create_memory_engine()
    service = FeedbackService(engine)
    try:
        success, message = service.submit_feedback(
            "missing-query", "user-1", "up", "no parent"
        )
        assert success is False
        assert message == "Query not found"

        with Session(engine) as session:
            session.add(
                Feedback(
                    query_id="missing-query",
                    user_id="user-1",
                    score="up",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_feedback_roundtrip_against_authoritative_schema():
    engine = create_memory_engine()
    service = FeedbackService(engine)
    try:
        with Session(engine) as session:
            query = Query(
                user_id="user-1",
                query="What is RAG?",
                answer="Retrieval-Augmented Generation",
                context={},
            )
            session.add(query)
            session.commit()
            session.refresh(query)
            query_id = query.id

        created, message = service.submit_feedback(query_id, "user-1", "up", "helpful")
        assert created is True
        assert message == "Feedback submitted successfully"

        duplicate, dup_message = service.submit_feedback(
            query_id, "user-1", "down", "changed mind"
        )
        assert duplicate is False
        assert dup_message == "Feedback already submitted for this query"

        history = service.get_user_feedback("user-1")
        assert len(history) == 1
        assert history[0]["score"] == "up"
        assert history[0]["comment"] == "helpful"
        assert history[0]["question"] == "What is RAG?"
        assert history[0]["response"] == "Retrieval-Augmented Generation"
        assert history[0]["query_id"] == query_id
    finally:
        engine.dispose()


def test_score_aggregation_and_date_window_without_sqlite_sql():
    source = Path("app/services/feedback_service.py").read_text()
    assert "PRAGMA" not in source
    assert "datetime('now'" not in source
    assert "table_info" not in source

    engine = create_memory_engine()
    service = FeedbackService(engine)
    try:
        with Session(engine) as session:
            recent = Query(
                user_id="user-1",
                query="recent question",
                answer="recent answer",
                context={},
            )
            old = Query(
                user_id="user-2",
                query="old question",
                answer="old answer",
                context={},
            )
            session.add(recent)
            session.add(old)
            session.commit()
            session.refresh(recent)
            session.refresh(old)

            session.add(
                Feedback(
                    query_id=recent.id,
                    user_id="user-1",
                    score="up",
                    created_at=datetime.utcnow(),
                )
            )
            session.add(
                Feedback(
                    query_id=recent.id,
                    user_id="user-2",
                    score="down",
                    created_at=datetime.utcnow(),
                )
            )
            session.add(
                Feedback(
                    query_id=old.id,
                    user_id="user-3",
                    score="up",
                    created_at=datetime.utcnow() - timedelta(days=30),
                )
            )
            session.commit()
            recent_id = recent.id

        stats = service.get_feedback_stats(recent_id)
        assert stats == {"up": 1, "down": 1}

        summary = service.get_feedback_summary(days=7)
        assert summary["total_feedback"] == 2
        assert summary["up_votes"] == 1
        assert summary["down_votes"] == 1
        assert summary["unique_users"] == 2
        assert summary["unique_messages"] == 1
        assert summary["satisfaction_rate"] == 50.0
    finally:
        engine.dispose()


def test_postgresql_dialect_compiles_schema_and_feedback_statements():
    """Exercise PostgreSQL compatibility without a live server."""
    pg = postgresql.dialect()
    sqlite_dialect = sqlite.dialect()

    for table in SQLModel.metadata.sorted_tables:
        if table.name not in EXPECTED_TABLES:
            continue
        pg_ddl = str(CreateTable(table).compile(dialect=pg)).lower()
        sqlite_ddl = str(CreateTable(table).compile(dialect=sqlite_dialect)).lower()
        assert "pragma" not in pg_ddl
        assert "datetime('now'" not in pg_ddl
        assert "pragma" not in sqlite_ddl
        if table.name == "feedback":
            assert "score" in pg_ddl
            assert "feedback.feedback" not in pg_ddl
            assert "references queries" in pg_ddl
        if table.name == "queries":
            assert "create table queries" in pg_ddl

    cutoff = datetime.utcnow() - timedelta(days=7)
    statement = select(Feedback).where(Feedback.created_at >= cutoff)
    compiled = str(
        statement.compile(dialect=pg, compile_kwargs={"literal_binds": True})
    ).lower()
    assert "pragma" not in compiled
    assert "datetime('now'" not in compiled
    assert "feedback.score" in compiled or "score" in compiled


@pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL", "").startswith("postgresql"),
    reason="Live PostgreSQL is not provisioned; dialect compilation covers the claim.",
)
def test_live_postgresql_schema_if_configured():
    url = os.environ["POSTGRES_TEST_URL"]
    engine = create_engine(url)
    try:
        apply_schema(engine)
        _assert_intended_schema(schema_snapshot(engine))
    finally:
        engine.dispose()
