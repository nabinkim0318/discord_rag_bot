# rag_agent/ingestion/schema.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PageMeta(BaseModel):
    doc_id: str
    source: str
    title: Optional[str] = None  # document title (if None, use file name)
    page: int  # 1-based page number
    section_title: Optional[str] = None
    url: Optional[str] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: str  # text normalization and then sha1
    extra: Dict[str, Any] = Field(default_factory=dict)


class PageRecord(BaseModel):
    text: str
    meta: PageMeta
