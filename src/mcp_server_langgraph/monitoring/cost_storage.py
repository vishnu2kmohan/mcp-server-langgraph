"""
CostStorageBackend - Storage backends for cost metrics.

Extracted from CostMetricsCollector as part of Phase 2.2 SRP decomposition.

Responsibilities:
- Protocol definition for storage backends
- In-memory storage implementation
- Record filtering and retrieval

Reference: Plan - Phase 2.2 SRP: Decompose CostMetricsCollector
"""

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
