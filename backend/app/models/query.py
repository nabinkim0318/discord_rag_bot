# app/models/query.py
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Query(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: Optional[str] = None
    query: str
    answer: str
    context: Dict[str, Any] = Field(
        sa_column=Column(JSON)
    )  # Retrieval documents' contents
    created_at: datetime = Field(default_factory=datetime.utcnow)
