# app/core/request_id.py
"""Canonical request-ID generation and lookup."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Request

MAX_REQUEST_ID_LENGTH = 64


def canonical_request_id(raw: str | None) -> str:
    """Return a UUID string: honor a valid caller ID, otherwise generate one."""
    if raw is None:
        return str(uuid4())
    candidate = str(raw).strip()
    if not candidate or len(candidate) > MAX_REQUEST_ID_LENGTH:
        return str(uuid4())
    try:
        return str(UUID(candidate))
    except (ValueError, AttributeError, TypeError):
        return str(uuid4())


def get_request_id(request: Request) -> str:
    """Read the middleware-assigned request ID, with a safe fallback."""
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    return canonical_request_id(request.headers.get("X-Request-ID"))
