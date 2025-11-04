"""
Database session management for async PostgreSQL connections.

This module provides async SQLAlchemy session management with connection pooling
and automatic cleanup.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from mcp_server_langgraph.database.models import Base

logger = logging.getLogger(__name__)

# Global engine instance (lazy-initialized)
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """
    Get or create the async database engine.

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
                     Example: postgresql+asyncpg://user:pass@localhost/dbname
        echo: Whether to echo SQL statements (for debugging)

    Returns:
        AsyncEngine instance

    Example:
        >>> engine = get_engine("postgresql+asyncpg://postgres:postgres@localhost/cost_tracking")
    """
    global _engine

    if _engine is None:
        logger.info(f"Creating async database engine: {database_url.split('@')[-1]}")

        _engine = create_async_engine(
            database_url,
            echo=echo,
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Max additional connections beyond pool_size
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

    return _engine


def get_session_maker(database_url: str, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session maker.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Returns:
        async_sessionmaker instance
    """
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_engine(database_url, echo)
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Manual commit control
        )

    return _async_session_maker


@asynccontextmanager
async def get_async_session(
    database_url: str, echo: bool = False
) -> AsyncGenerator[AsyncSession, None]:
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
    Initialize the database schema.

    Creates all tables defined in models if they don't exist.
    This is idempotent - safe to call multiple times.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Example:
        >>> await init_database("postgresql+asyncpg://postgres:postgres@localhost/cost_tracking")
    """
    engine = get_engine(database_url, echo)

    logger.info("Initializing database schema...")

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database schema initialized successfully")


async def cleanup_database() -> None:
    """
    Cleanup database resources.

    Closes all connections and disposes the engine.
    Should be called on application shutdown.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Cleaning up database connections...")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("Database cleanup complete")
