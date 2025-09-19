# app/core/retry.py
"""
Retry logic and Circuit Breaker pattern implementation
"""

import asyncio
import functools
import time
from enum import Enum
from typing import Callable, Dict, List, Optional, Type

from app.core.exceptions import ExternalServiceException
from app.core.logging import logger


class CircuitState(Enum):
    """Circuit Breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            ExternalServiceException,
        ]


class CircuitBreakerConfig:
    """Configuration for Circuit Breaker"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Optional[Type[Exception]] = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception or ExternalServiceException


class CircuitBreaker:
    """Circuit Breaker implementation"""

    def __init__(self, config: CircuitBreakerConfig, name: str = "default"):
        self.config = config
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

    def can_execute(self) -> bool:
        """Check if request can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Require 2 successes to close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' moved to CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def on_failure(self, exception: Exception):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' moved to OPEN "
                f"(failures: {self.failure_count})"
            )
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' moved back to OPEN")


class RetryManager:
    """Manages retry logic and circuit breakers"""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig
    ) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(config, name)
        return self.circuit_breakers[name]

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt"""
        delay = config.base_delay * (config.exponential_base ** (attempt - 1))
        delay = min(delay, config.max_delay)

        if config.jitter:
            # Add random jitter to prevent thundering herd
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay

    def is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """Check if exception is retryable"""
        return any(
            isinstance(exception, exc_type) for exc_type in config.retryable_exceptions
        )


# Global retry manager
retry_manager = RetryManager()


def retry_with_circuit_breaker(
    retry_config: RetryConfig = None,
    circuit_breaker_config: CircuitBreakerConfig = None,
    circuit_breaker_name: str = "default",
):
    """
    Decorator for retry logic with circuit breaker

    Args:
        retry_config: Retry configuration
        circuit_breaker_config: Circuit breaker configuration
        circuit_breaker_name: Name for circuit breaker instance
    """
    if retry_config is None:
        retry_config = RetryConfig()
    if circuit_breaker_config is None:
        circuit_breaker_config = CircuitBreakerConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            circuit_breaker = retry_manager.get_circuit_breaker(
                circuit_breaker_name, circuit_breaker_config
            )

            # Check circuit breaker
            if not circuit_breaker.can_execute():
                raise ExternalServiceException(
                    f"Circuit breaker '{circuit_breaker_name}' is OPEN",
                    service_name=circuit_breaker_name,
                )

            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    circuit_breaker.on_success()
                    return result

                except Exception as e:
                    last_exception = e
                    circuit_breaker.on_failure(e)

                    # Check if exception is retryable
                    if not retry_manager.is_retryable_exception(e, retry_config):
                        logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                        raise e

                    if attempt < retry_config.max_attempts:
                        delay = retry_manager.calculate_delay(attempt, retry_config)
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {retry_config.max_attempts} attempts failed "
                            f"for {func.__name__}"
                        )

            # All attempts failed
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            circuit_breaker = retry_manager.get_circuit_breaker(
                circuit_breaker_name, circuit_breaker_config
            )

            # Check circuit breaker
            if not circuit_breaker.can_execute():
                raise ExternalServiceException(
                    f"Circuit breaker '{circuit_breaker_name}' is OPEN",
                    service_name=circuit_breaker_name,
                )

            last_exception = None

            for attempt in range(1, retry_config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    circuit_breaker.on_success()
                    return result

                except Exception as e:
                    last_exception = e
                    circuit_breaker.on_failure(e)

                    # Check if exception is retryable
                    if not retry_manager.is_retryable_exception(e, retry_config):
                        logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                        raise e

                    if attempt < retry_config.max_attempts:
                        delay = retry_manager.calculate_delay(attempt, retry_config)
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {retry_config.max_attempts} attempts failed "
                            f"for {func.__name__}"
                        )

            # All attempts failed
            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Convenience decorators for common use cases
def retry_weaviate(max_attempts: int = 3):
    """Retry decorator for Weaviate operations"""
    return retry_with_circuit_breaker(
        retry_config=RetryConfig(max_attempts=max_attempts, base_delay=0.5),
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=30.0
        ),
        circuit_breaker_name="weaviate",
    )


def retry_openai(max_attempts: int = 3):
    """Retry decorator for OpenAI API calls"""
    return retry_with_circuit_breaker(
        retry_config=RetryConfig(max_attempts=max_attempts, base_delay=1.0),
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=60.0
        ),
        circuit_breaker_name="openai",
    )


def retry_database(max_attempts: int = 3):
    """Retry decorator for database operations"""
    return retry_with_circuit_breaker(
        retry_config=RetryConfig(max_attempts=max_attempts, base_delay=0.1),
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=10, recovery_timeout=30.0
        ),
        circuit_breaker_name="database",
    )
