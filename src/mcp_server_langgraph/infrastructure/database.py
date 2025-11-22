"""
Database Connection Infrastructure

Provides reusable database connection functionality with retry logic.
Separates I/O concerns from business logic for better testability.
"""

import asyncio
from typing import Protocol

import asyncpg

from mcp_server_langgraph.utils.retry import retry_with_backoff


class DatabaseConfig(Protocol):
    """Protocol for database configuration"""

    gdpr_postgres_url: str


async def check_database_connectivity(postgres_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """
    Check if PostgreSQL database is accessible.

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
    try:
        # Try to connect to PostgreSQL (with timeout)
        try:
            conn = await asyncio.wait_for(asyncpg.connect(postgres_url), timeout=timeout)
            await conn.close()
            return True, "PostgreSQL database accessible"
        except asyncio.TimeoutError:
            return False, f"PostgreSQL connection timeout ({timeout}s)"
        except asyncpg.InvalidPasswordError as e:
            return False, f"PostgreSQL authentication failed: {e}"
        except asyncpg.PostgresError as e:
            # Check if it's a missing database error
            if "does not exist" in str(e):
                return False, f"PostgreSQL database does not exist: {e}"
            return False, f"PostgreSQL error: {e}"
        except ValueError as e:
            return False, f"Invalid PostgreSQL connection string: {e}"
        except Exception as e:
            return False, f"PostgreSQL connection failed: {e}"

    except ImportError:
        return False, "asyncpg not installed - cannot validate database connectivity"
    except Exception as e:
        return False, f"Unexpected error during database validation: {e}"


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
    Create PostgreSQL connection pool with retry logic.

    Uses exponential backoff to handle transient connection failures.

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

    Example:
        >>> pool = await create_connection_pool(
        ...     "postgresql://postgres:postgres@localhost:5432/gdpr"
        ... )
        >>> # Use pool for queries
        >>> await pool.close()
    """

    async def _create_pool() -> asyncpg.Pool:
        """Helper to create connection pool"""
        pool = await asyncpg.create_pool(
            postgres_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
        if pool is None:
            raise RuntimeError("Failed to create connection pool")
        return pool

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

    return pool
