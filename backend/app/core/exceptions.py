# app/core/exceptions.py
"""
Custom exception classes
"""

from typing import Any, Dict, Optional


class RAGException(Exception):
    """RAG pipeline related exception"""

    def __init__(
        self,
        message: str,
        error_code: str = "RAG_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(Exception):
    """Database related exception"""

    def __init__(
        self,
        message: str,
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(Exception):
    """Input validation related exception"""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ExternalServiceException(Exception):
    """External service call related exception"""

    def __init__(
        self,
        message: str,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        service_name: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.service_name = service_name
        self.details = details or {}
        super().__init__(self.message)
