"""
CostStorageBackend - Storage backends for cost metrics.

Extracted from CostMetricsCollector as part of Phase 2.2 SRP decomposition.

Responsibilities:
- Protocol definition for storage backends
- In-memory storage implementation
- PostgreSQL storage implementation
- Record filtering and retrieval

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage


@runtime_checkable
class CostStorageBackend(Protocol):
    """
    Protocol for cost storage backends.

    Defines the interface for storing and retrieving TokenUsage records.
    Implementations can use in-memory storage, PostgreSQL, or other backends.
    """

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record.

        Args:
            record: TokenUsage record to store
        """
        ...

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[TokenUsage]:
        """
        Get stored records with optional filtering.

        Args:
            filters: Optional filters (e.g., {"user_id": "user:alice"})

        Returns:
            List of matching TokenUsage records
        """
        ...

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        ...

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        ...

    @property
    def total_records(self) -> int:
        """Get the total number of stored records."""
        ...


class MemoryCostStorage:
    """
    In-memory storage backend for cost metrics.

    Thread-safe implementation using asyncio.Lock.
    Suitable for development, testing, and single-instance deployments.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._records: list[TokenUsage] = []
        self._lock = asyncio.Lock()

    @property
    def total_records(self) -> int:
        """Get the total number of stored records."""
        return len(self._records)

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record.

        Args:
            record: TokenUsage record to store
        """
        async with self._lock:
            self._records.append(record)

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[TokenUsage]:
        """
        Get stored records with optional filtering.

        Supports filters:
        - user_id: Filter by user identifier
        - model: Filter by model name
        - provider: Filter by provider name
        - session_id: Filter by session identifier

        Args:
            filters: Optional filters dictionary

        Returns:
            List of matching TokenUsage records
        """
        async with self._lock:
            records = self._records.copy()

        if not filters:
            return records

        # Apply filters
        for field, value in filters.items():
            records = [r for r in records if getattr(r, field, None) == value]

        return records

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        async with self._lock:
            initial_count = len(self._records)
            self._records = [r for r in self._records if r.timestamp >= cutoff]
            return initial_count - len(self._records)

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        async with self._lock:
            return self._records[-1] if self._records else None


class PostgresCostStorage:
    """
    PostgreSQL storage backend for cost metrics.

    Provides persistent storage for token usage records with full
    CRUD operations via SQLAlchemy async session.

    Suitable for production deployments requiring durability and
    multi-instance consistency.
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize PostgreSQL storage.

        Args:
            database_url: PostgreSQL connection URL (postgresql+asyncpg://...)

        Raises:
            ValueError: If database_url is None or empty
        """
        if not database_url:
            msg = "database_url is required for PostgresCostStorage"
            raise ValueError(msg)

        self._database_url = database_url
        self._record_count = 0

    @property
    def total_records(self) -> int:
        """Get the total number of stored records (tracked locally)."""
        return self._record_count

    async def store(self, record: TokenUsage) -> None:
        """
        Store a token usage record in PostgreSQL.

        Args:
            record: TokenUsage record to store
        """
        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            db_record = TokenUsageRecord(
                timestamp=record.timestamp,
                user_id=record.user_id,
                session_id=record.session_id,
                model=record.model,
                provider=record.provider,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                estimated_cost_usd=record.estimated_cost_usd,
                feature=record.feature,
                metadata_=record.metadata,
            )
            session.add(db_record)
            # Session commits automatically via context manager

        self._record_count += 1

    async def get_records(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[TokenUsage]:
        """
        Get stored records with optional filtering.

        Supports filters:
        - user_id: Filter by user identifier
        - model: Filter by model name
        - provider: Filter by provider name
        - session_id: Filter by session identifier

        Args:
            filters: Optional filters dictionary

        Returns:
            List of matching TokenUsage records
        """
        from sqlalchemy import select

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            stmt = select(TokenUsageRecord).order_by(TokenUsageRecord.timestamp.desc())

            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(TokenUsageRecord, field):
                        stmt = stmt.where(getattr(TokenUsageRecord, field) == value)

            result = await session.execute(stmt)
            db_records = result.scalars().all()

            # Convert to TokenUsage objects
            return [self._to_token_usage(r) for r in db_records]

    async def delete_records_before(self, cutoff: datetime) -> int:
        """
        Delete records older than the cutoff time.

        Args:
            cutoff: Delete records with timestamp before this time

        Returns:
            Number of records deleted
        """
        from sqlalchemy import delete

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            stmt = delete(TokenUsageRecord).where(TokenUsageRecord.timestamp < cutoff)
            result = await session.execute(stmt)
            # CursorResult has rowcount, but Result[Any] type doesn't expose it
            deleted_count: int = getattr(result, "rowcount", 0) or 0

        # Update local count (approximate)
        self._record_count = max(0, self._record_count - deleted_count)

        return deleted_count

    async def get_latest_record(self) -> TokenUsage | None:
        """
        Get the most recently stored record.

        Returns:
            Latest TokenUsage record or None if empty
        """
        from sqlalchemy import select

        from mcp_server_langgraph.database import get_async_session
        from mcp_server_langgraph.database.models import TokenUsageRecord

        async with get_async_session(self._database_url) as session:
            stmt = select(TokenUsageRecord).order_by(TokenUsageRecord.timestamp.desc()).limit(1)
            result = await session.execute(stmt)
            db_record = result.scalars().first()

            if db_record is None:
                return None

            return self._to_token_usage(db_record)

    def _to_token_usage(self, db_record: Any) -> TokenUsage:
        """
        Convert database record to TokenUsage.

        Args:
            db_record: TokenUsageRecord from database

        Returns:
            TokenUsage instance
        """
        return TokenUsage(
            timestamp=db_record.timestamp,
            user_id=db_record.user_id,
            session_id=db_record.session_id,
            model=db_record.model,
            provider=db_record.provider,
            prompt_tokens=db_record.prompt_tokens,
            completion_tokens=db_record.completion_tokens,
            total_tokens=db_record.total_tokens,
            estimated_cost_usd=db_record.estimated_cost_usd,
            feature=db_record.feature,
            metadata=db_record.metadata_ or {},
        )
