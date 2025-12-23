"""
Database Connection Infrastructure

Provides reusable database connection functionality with retry logic.
Separates I/O concerns from business logic for better testability.

Resilience patterns (ADR-0026):
- Retry with exponential backoff (2.0x) for transient failures
- Circuit breaker to fail fast when PostgreSQL is repeatedly unavailable
"""

import asyncio
import logging
from typing import Protocol

import asyncpg
import pybreaker

from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker
from mcp_server_langgraph.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class DatabaseConfig(Protocol):
    """Protocol for database configuration"""

    gdpr_postgres_url: str


async def check_database_connectivity(postgres_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """
    Check if PostgreSQL database is accessible.

    Uses circuit breaker to fail fast when PostgreSQL is repeatedly unavailable,
    and retry with exponential backoff for transient failures.

    Args:
        postgres_url: PostgreSQL connection URL
        timeout: Connection timeout in seconds (default: 5.0)

    Returns:
        Tuple of (is_healthy, message)

    Example:
        >>> is_healthy, message = await check_database_connectivity(
        ...     "postgresql://user:pass@localhost:5432/db"
        ... )
        >>> if is_healthy:
        ...     print("Database is accessible")
    """
    # Check circuit breaker - fail fast if circuit is OPEN
    breaker = get_circuit_breaker("postgres")
    if breaker.current_state == pybreaker.STATE_OPEN:
        logger.debug("PostgreSQL circuit breaker open, skipping connectivity check")
        return False, "PostgreSQL circuit breaker OPEN - service unavailable"

    # Retry with exponential backoff
    max_attempts = 3
    base_delay = 1.0
    backoff_multiplier = 2.0

    for attempt in range(1, max_attempts + 1):
        try:
            # Try to connect to PostgreSQL (with timeout)
            try:
                conn = await asyncio.wait_for(asyncpg.connect(postgres_url), timeout=timeout)
                await conn.close()

                # Success - notify circuit breaker
                breaker.state.on_success()
                return True, "PostgreSQL database accessible"

            except TimeoutError:
                return False, f"PostgreSQL connection timeout ({timeout}s)"
            except asyncpg.InvalidPasswordError as e:
                # Authentication errors are not transient - don't retry
                return False, f"PostgreSQL authentication failed: {e}"
            except asyncpg.PostgresError as e:
                # Check if it's a missing database error (not transient)
                if "does not exist" in str(e):
                    return False, f"PostgreSQL database does not exist: {e}"
                return False, f"PostgreSQL error: {e}"
            except ValueError as e:
                # Invalid connection string - not transient
                return False, f"Invalid PostgreSQL connection string: {e}"

        except OSError as e:
            # Transient connection error - retry with backoff
            if attempt < max_attempts:
                delay = base_delay * (backoff_multiplier ** (attempt - 1))
                logger.warning(
                    f"PostgreSQL connectivity check failed (attempt {attempt}/{max_attempts}), retrying in {delay:.1f}s: {e}",
                    extra={"attempt": attempt},
                )
                await asyncio.sleep(delay)
                continue

            # All retries exhausted - record failure for circuit breaker
            logger.error(f"PostgreSQL connectivity check failed after {max_attempts} attempts: {e}")
            try:
                breaker._inc_counter()
                breaker.state.on_failure(e)
            except pybreaker.CircuitBreakerError:
                logger.debug("PostgreSQL circuit breaker opened due to repeated failures")
            return False, f"PostgreSQL connection failed: {e}"

        except ImportError:
            return False, "asyncpg not installed - cannot validate database connectivity"
        except Exception as e:
            # Unexpected error - record failure for circuit breaker
            logger.error(f"Unexpected error during database validation: {e}")
            try:
                breaker._inc_counter()
                breaker.state.on_failure(e)
            except pybreaker.CircuitBreakerError:
                logger.debug("PostgreSQL circuit breaker opened due to repeated failures")
            return False, f"Unexpected error during database validation: {e}"

    return False, "PostgreSQL connection check exhausted all retries"


async def create_connection_pool(
    postgres_url: str,
    min_size: int = 2,
    max_size: int = 10,
    command_timeout: float = 60.0,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 8.0,
) -> asyncpg.Pool:
    """
    Create PostgreSQL connection pool with retry logic and circuit breaker.

    Uses exponential backoff to handle transient connection failures,
    and circuit breaker to fail fast when PostgreSQL is repeatedly unavailable.

    Args:
        postgres_url: PostgreSQL connection URL
        min_size: Minimum pool size (default: 2)
        max_size: Maximum pool size (default: 10)
        command_timeout: Command timeout in seconds (default: 60.0)
        max_retries: Maximum retry attempts (default: 3)
        initial_delay: Initial retry delay in seconds (default: 1.0)
        max_delay: Maximum retry delay in seconds (default: 8.0)

    Returns:
        asyncpg.Pool instance

    Raises:
        RuntimeError: If pool creation fails
        asyncpg.PostgresError: If connection fails after retries
        pybreaker.CircuitBreakerError: If circuit breaker is OPEN

    Example:
        >>> pool = await create_connection_pool(
        ...     "postgresql://postgres:postgres@localhost:5432/gdpr"
        ... )
        >>> # Use pool for queries
        >>> await pool.close()
    """
    # Check circuit breaker - fail fast if circuit is OPEN
    breaker = get_circuit_breaker("postgres")
    if breaker.current_state == pybreaker.STATE_OPEN:
        logger.debug("PostgreSQL circuit breaker open, skipping pool creation")
        raise pybreaker.CircuitBreakerError(breaker)

    async def _create_pool() -> asyncpg.Pool:
        """Helper to create connection pool"""
        pool = await asyncpg.create_pool(
            postgres_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
        if pool is None:
            msg = "Failed to create connection pool"
            raise RuntimeError(msg)
        return pool

    try:
        # Create connection pool with retry logic
        # Retries: 3, Backoff: 1s, 2s, 4s (with jitter)
        pool = await retry_with_backoff(
            _create_pool,
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=2.0,
            jitter=True,
            max_timeout=60.0,
        )

        # Success - notify circuit breaker
        breaker.state.on_success()
        return pool

    except Exception as e:
        # Record failure for circuit breaker
        logger.error(f"PostgreSQL pool creation failed: {e}")
        try:
            breaker._inc_counter()
            breaker.state.on_failure(e)
        except pybreaker.CircuitBreakerError:
            logger.debug("PostgreSQL circuit breaker opened due to repeated failures")
        raise
