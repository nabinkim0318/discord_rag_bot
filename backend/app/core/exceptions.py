# app/core/exceptions.py
"""
커스텀 예외 클래스들
"""

from typing import Any, Dict, Optional


class RAGException(Exception):
    """RAG 파이프라인 관련 예외"""

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
    """데이터베이스 관련 예외"""

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
    """입력 검증 관련 예외"""

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
    """외부 서비스 호출 관련 예외"""

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
