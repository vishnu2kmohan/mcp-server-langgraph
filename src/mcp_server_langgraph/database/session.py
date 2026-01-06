"""
Database session management for async PostgreSQL connections.

This module provides async SQLAlchemy session management with connection pooling
and automatic cleanup.

URL-Keyed Registry (ADR-0091):
- Supports multiple database URLs without collision (main vs compliance DB)
- Uses threading.Lock for thread-safe singleton creation
- Double-checked locking pattern for performance
- dispose_all_engines() for proper cleanup on shutdown
"""

import logging
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


logger = logging.getLogger(__name__)

# URL-keyed registries for multi-database support
# This replaces the single global _engine pattern to support multiple database URLs
# (e.g., main database vs compliance/GDPR database) without collision
_engines: dict[str, AsyncEngine] = {}
_session_makers: dict[str, async_sessionmaker[AsyncSession]] = {}
# Use RLock (reentrant lock) because get_session_maker() calls get_engine()
# which would deadlock with a regular Lock
_engine_lock = threading.RLock()  # Thread-safe, supports nested acquisition

# Legacy globals for backward compatibility (deprecated, will be removed)
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """
    Get or create the async database engine for a given URL.

    Uses URL-keyed registry with double-checked locking pattern:
    - Fast path: Return existing engine if URL already registered
    - Slow path: Acquire lock, double-check, create if needed

    This allows multiple database URLs to be used without collision
    (e.g., main database vs compliance/GDPR database).

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
                     Example: postgresql+asyncpg://user:pass@localhost/dbname
        echo: Whether to echo SQL statements (for debugging)

    Returns:
        AsyncEngine instance for the given URL

    Example:
        >>> engine = get_engine("postgresql+asyncpg://postgres:postgres@localhost/cost_tracking")
        >>> compliance_engine = get_engine("postgresql+asyncpg://postgres:postgres@localhost/compliance")
        >>> engine is not compliance_engine  # Different URLs = different engines
        True
    """
    global _engine

    # Fast path: Check without lock (double-checked locking)
    if database_url in _engines:
        return _engines[database_url]

    # Slow path: Acquire lock and create engine if needed
    with _engine_lock:
        # Double-check after acquiring lock (another thread may have created it)
        if database_url not in _engines:
            logger.info(f"Creating async database engine: {database_url.split('@')[-1]}")

            engine = create_async_engine(
                database_url,
                echo=echo,
                pool_size=10,  # Connection pool size
                max_overflow=20,  # Max additional connections beyond pool_size
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
            )
            _engines[database_url] = engine

            # Also set legacy global for backward compatibility
            if _engine is None:
                _engine = engine

        return _engines[database_url]


def get_session_maker(database_url: str, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session maker for a given URL.

    Uses URL-keyed registry to support multiple database URLs.
    Each URL gets its own session maker bound to the corresponding engine.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Returns:
        async_sessionmaker instance for the given URL
    """
    global _async_session_maker

    # Fast path: Check without lock
    if database_url in _session_makers:
        return _session_makers[database_url]

    # Slow path: Create session maker if needed
    with _engine_lock:
        # Double-check after acquiring lock
        if database_url not in _session_makers:
            engine = get_engine(database_url, echo)
            session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Don't expire objects after commit
                autoflush=False,  # Manual flush control
                autocommit=False,  # Manual commit control
            )
            _session_makers[database_url] = session_maker

            # Also set legacy global for backward compatibility
            if _async_session_maker is None:
                _async_session_maker = session_maker

        return _session_makers[database_url]


@asynccontextmanager
async def get_async_session(database_url: str, echo: bool = False) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Automatically handles session lifecycle:
    - Creates session
    - Commits on success
    - Rolls back on exception
    - Closes session

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Yields:
        AsyncSession instance

    Example:
        >>> async with get_async_session(db_url) as session:
        ...     result = await session.execute(select(TokenUsageRecord))
        ...     records = result.scalars().all()
    """
    session_maker = get_session_maker(database_url, echo)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database(database_url: str, echo: bool = False) -> None:
    """
    Initialize the database connection.

    IMPORTANT: This function NO LONGER creates tables via create_all().
    All schema management is handled exclusively by Alembic migrations.

    To apply schema changes:
        1. Create migration: alembic revision --autogenerate -m "description"
        2. Apply migration: alembic upgrade head

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Example:
        >>> await init_database("postgresql+asyncpg://postgres:postgres@localhost/cost_tracking")

    Note:
        Run 'alembic upgrade head' before starting the application to ensure
        the database schema is up to date.
    """
    # Initialize the engine (validates connection can be established)
    get_engine(database_url, echo)

    logger.info(
        "Database connection initialized. Schema is managed by Alembic migrations - run 'alembic upgrade head' if needed."
    )


async def cleanup_database() -> None:
    """
    Cleanup database resources (legacy - use dispose_all_engines() instead).

    Closes all connections and disposes the engine.
    Should be called on application shutdown.

    DEPRECATED: This only cleans up the legacy global engine.
    Use dispose_all_engines() to clean up all engines in the registry.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Cleaning up database connections...")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("Database cleanup complete")


async def dispose_all_engines() -> None:
    """
    Dispose all engines in the URL-keyed registry.

    This is the preferred cleanup function for application shutdown.
    It properly disposes ALL registered engines and clears the registries.

    Safe to call even if no engines have been created.

    Called from:
    - mcp/server_streamable.py (Streamable HTTP lifespan)
    - infrastructure/app_factory.py (stdio lifespan)

    Note:
        Some modules build their own engines (compliance/gdpr, workflow managers)
        and are not covered by this cleanup. Those modules must manage their
        own cleanup separately.

    Example:
        >>> from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients
        >>> await cleanup_all_clients()  # Calls dispose_all_engines() internally
    """
    global _engine, _async_session_maker

    if not _engines:
        logger.debug("No database engines to dispose (registry empty)")
        return

    logger.info(f"Disposing {len(_engines)} database engine(s)...")

    for url, engine in list(_engines.items()):
        try:
            await engine.dispose()
            # Mask password in URL for logging
            safe_url = url.split("@")[-1] if "@" in url else url
            logger.debug(f"Disposed engine for: {safe_url}")
        except Exception as e:
            logger.warning(f"Error disposing engine: {e}")

    # Clear registries
    _engines.clear()
    _session_makers.clear()

    # Also clear legacy globals
    _engine = None
    _async_session_maker = None

    logger.info("All database engines disposed")
