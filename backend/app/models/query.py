# app/models/query.py
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlmodel import Field, SQLModel

try:
    from sqlalchemy.dialects.postgresql import JSONB

    PG_JSONB = JSONB
except Exception:
    PG_JSONB = None

from app.db.session import engine as _engine

_dialect = _engine.url.get_backend_name()
_json_col = (
    Column(SQLITE_JSON)
    if _dialect == "sqlite"
    else Column(PG_JSONB if PG_JSONB else SQLITE_JSON)
)


class Query(SQLModel, table=True):
    __tablename__ = "queries"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    query: str
    answer: str

    # JSON column with dialect-specific type
    context: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=_json_col,
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
