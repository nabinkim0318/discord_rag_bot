# app/models/query.py
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Query(SQLModel, table=True):
    __tablename__ = "queries"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    query: str
    answer: str

    context: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
