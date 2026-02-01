"""
LangGraph Execution Trace Repository.

Provides storage and retrieval of LangGraph node execution traces for:
- Historical trace display in DevTools AgentTraceTab
- GDPR export/delete compliance

Follows existing pattern from repositories/decision_trace.py:
- ABC base class for abstraction
- PostgresLangGraphExecutionTraceRepository concrete implementation
- DI via session factory

Key Features:
- Append-only execution trace storage (WHAT nodes ran, not WHY)
- Batch insert for async efficiency
- Session-based query for timeline views
- GDPR export/delete by user
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

from sqlalchemy import delete, select

from mcp_server_langgraph.database.models import LangGraphExecutionTrace
from mcp_server_langgraph.storage.models import LangGraphExecutionTraceSummary

# Type alias for session factory
SessionFactory = Callable[[], Any]  # Returns context manager yielding AsyncSession


class LangGraphExecutionTraceRepositoryBase(ABC):
    """Abstract base class for LangGraph execution trace repository.

    Defines the interface for storing and retrieving execution traces.
    Implementations should handle persistence to specific backends.
    """

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> str:
        """Create a single execution trace.

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
    async def get_by_session(self, session_id: str, limit: int = 100, offset: int = 0) -> list[LangGraphExecutionTraceSummary]:
        """Get traces for a session with pagination.

        Args:
            session_id: Session identifier
            limit: Maximum traces to return
            offset: Pagination offset

        Returns:
            List of LangGraphExecutionTraceSummary for timeline display
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

        Args:
            user_id: User identifier

        Returns:
            Count of deleted traces
        """
        ...


class PostgresLangGraphExecutionTraceRepository(LangGraphExecutionTraceRepositoryBase):
    """PostgreSQL implementation of LangGraph execution trace repository.

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
        """Create a single execution trace."""
        async with self._session_factory() as session:
            trace = LangGraphExecutionTrace(**data)
            session.add(trace)
            await session.commit()
            return trace.trace_id

    async def create_batch(self, data: list[dict[str, Any]]) -> int:
        """Batch insert for async worker efficiency."""
        if not data:
            return 0

        async with self._session_factory() as session:
            traces = [LangGraphExecutionTrace(**d) for d in data]
            session.add_all(traces)
            await session.commit()
            return len(traces)

    async def get_by_session(self, session_id: str, limit: int = 100, offset: int = 0) -> list[LangGraphExecutionTraceSummary]:
        """Get traces for session with pagination."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LangGraphExecutionTrace)
                .where(LangGraphExecutionTrace.session_id == session_id)
                .order_by(LangGraphExecutionTrace.start_time, LangGraphExecutionTrace.sequence_number)
                .limit(limit)
                .offset(offset)
            )
            return [
                LangGraphExecutionTraceSummary(
                    trace_id=t.trace_id,
                    node_name=t.node_name,
                    status=t.status,
                    start_time=t.start_time,
                    end_time=t.end_time,
                    duration_ms=t.duration_ms,
                    sequence_number=t.sequence_number,
                )
                for t in result.scalars().all()
            ]

    async def get_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all user traces for GDPR export."""
        async with self._session_factory() as session:
            result = await session.execute(select(LangGraphExecutionTrace).where(LangGraphExecutionTrace.user_id == user_id))
            return [t.to_dict() for t in result.scalars().all()]

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all user traces for GDPR."""
        async with self._session_factory() as session:
            result = await session.execute(delete(LangGraphExecutionTrace).where(LangGraphExecutionTrace.user_id == user_id))
            await session.commit()
            return int(result.rowcount or 0)
