"""
Decision Trace Repository.

Provides storage and retrieval of decision traces for context graphs.

Follows existing pattern from repositories/audit_log.py:
- ABC base class for abstraction
- PostgresDecisionTraceRepository concrete implementation
- DI via session factory

Key Features:
- Append-only decision trace storage (the "WHY" behind agent decisions)
- Batch insert for async worker efficiency
- GDPR export/delete by user
- Retention cleanup for expired traces
- Session-based query for timeline views

Reference: ADR-0101 Context Graphs
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from sqlalchemy import delete, select

# Type alias for session factory
SessionFactory = Callable[[], Any]  # Returns context manager yielding AsyncSession

from mcp_server_langgraph.database.models import DecisionTrace
from mcp_server_langgraph.storage.models import (
    DecisionTraceRead,
    DecisionTraceSummary,
)


class DecisionTraceRepositoryBase(ABC):
    """Abstract base class for decision trace repository.

    Defines the interface for storing and retrieving decision traces.
    Implementations should handle persistence to specific backends.
    """

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> str:
        """Create a single decision trace.

        Args:
            data: Dictionary with trace data including trace_id

        Returns:
            The trace_id of the created trace
        """
        ...

    @abstractmethod
    async def create_batch(self, data: list[dict[str, Any]]) -> int:
        """Batch insert multiple traces.

        Optimized for async worker efficiency.

        Args:
            data: List of trace data dictionaries

        Returns:
            Count of inserted traces
        """
        ...

    @abstractmethod
    async def get_by_id(self, trace_id: str) -> DecisionTraceRead | None:
        """Get a trace by its unique ID.

        Args:
            trace_id: Unique trace identifier

        Returns:
            DecisionTraceRead model or None if not found
        """
        ...

    @abstractmethod
    async def get_by_session(self, session_id: str, limit: int = 100, offset: int = 0) -> list[DecisionTraceSummary]:
        """Get traces for a session with pagination.

        Args:
            session_id: Session identifier
            limit: Maximum traces to return
            offset: Pagination offset

        Returns:
            List of DecisionTraceSummary for timeline display
        """
        ...

    @abstractmethod
    async def get_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all traces for a user (GDPR export).

        Args:
            user_id: User identifier (e.g., "user:alice")

        Returns:
            List of trace dictionaries for export
        """
        ...

    @abstractmethod
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all traces for a user (GDPR deletion).

        Edges are deleted by CASCADE constraint.

        Args:
            user_id: User identifier

        Returns:
            Count of deleted traces
        """
        ...

    @abstractmethod
    async def delete_expired(self, retention_days: int) -> int:
        """Delete traces older than retention period.

        Edges are deleted by CASCADE constraint.

        Args:
            retention_days: Number of days to retain

        Returns:
            Count of deleted traces
        """
        ...


class PostgresDecisionTraceRepository(DecisionTraceRepositoryBase):
    """PostgreSQL implementation of decision trace repository.

    Uses async session factory for connection pooling.
    All methods use context managers for proper session lifecycle.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize with async session factory.

        Args:
            session_factory: Callable that returns async context manager for sessions
        """
        self._session_factory = session_factory

    async def create(self, data: dict[str, Any]) -> str:
        """Create a single decision trace."""
        async with self._session_factory() as session:
            trace = DecisionTrace(**data)
            session.add(trace)
            await session.commit()
            return trace.trace_id

    async def create_batch(self, data: list[dict[str, Any]]) -> int:
        """Batch insert for async worker efficiency."""
        if not data:
            return 0

        async with self._session_factory() as session:
            traces = [DecisionTrace(**d) for d in data]
            session.add_all(traces)
            await session.commit()
            return len(traces)

    async def get_by_id(self, trace_id: str) -> DecisionTraceRead | None:
        """Get trace by ID."""
        async with self._session_factory() as session:
            result = await session.execute(select(DecisionTrace).where(DecisionTrace.trace_id == trace_id))
            trace = result.scalar_one_or_none()
            return DecisionTraceRead.model_validate(trace) if trace else None

    async def get_by_session(self, session_id: str, limit: int = 100, offset: int = 0) -> list[DecisionTraceSummary]:
        """Get traces for session with pagination."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(DecisionTrace)
                .where(DecisionTrace.session_id == session_id)
                .order_by(DecisionTrace.sequence_number)
                .limit(limit)
                .offset(offset)
            )
            return [
                DecisionTraceSummary(
                    trace_id=t.trace_id,
                    timestamp=t.timestamp,
                    decision_type=t.decision_type,
                    chosen_action=t.chosen_action,
                    confidence=float(t.confidence),
                    outcome=t.outcome,
                )
                for t in result.scalars().all()
            ]

    async def get_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all user traces for GDPR export."""
        async with self._session_factory() as session:
            result = await session.execute(select(DecisionTrace).where(DecisionTrace.user_id == user_id))
            return [t.to_dict() for t in result.scalars().all()]

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all user traces for GDPR (edges deleted by CASCADE)."""
        async with self._session_factory() as session:
            result = await session.execute(delete(DecisionTrace).where(DecisionTrace.user_id == user_id))
            await session.commit()
            return int(result.rowcount or 0)

    async def delete_expired(self, retention_days: int) -> int:
        """Delete traces older than retention period (edges deleted by CASCADE)."""
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        async with self._session_factory() as session:
            result = await session.execute(delete(DecisionTrace).where(DecisionTrace.timestamp < cutoff))
            await session.commit()
            return int(result.rowcount or 0)
