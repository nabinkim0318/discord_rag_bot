"""create queries and feedback tables

Revision ID: b7e2c4a91f03
Revises:
Create Date: 2026-08-23 19:41:00.000000

Replaces the stale initial revision that created `query` / `feedback.feedback`
instead of the intended SQLModel contract (`queries` / `feedback.score`).
This is a new baseline for a portfolio project with no production
migration history to preserve.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c4a91f03"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to the current SQLModel contract."""
    op.create_table(
        "queries",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("query", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("answer", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_queries_id"), "queries", ["id"], unique=False)
    op.create_index(op.f("ix_queries_user_id"), "queries", ["user_id"], unique=False)

    op.create_table(
        "feedback",
        sa.Column("query_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("score", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("comment", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("feedback")
    op.drop_index(op.f("ix_queries_user_id"), table_name="queries")
    op.drop_index(op.f("ix_queries_id"), table_name="queries")
    op.drop_table("queries")
