"""
Unit tests for LangGraphExecutionTraceRepository.

TDD RED Phase: Tests for ABC and Postgres implementation of LangGraph execution trace repository.

This repository stores LangGraph node execution traces for:
- Live monitoring via DevTools WebSocket (persisted for history)
- Historical trace retrieval after page reload
- GDPR export/delete compliance

Tests:
- ABC interface methods defined
- PostgresLangGraphExecutionTraceRepository CRUD operations
- Batch insert
- Query by session
- GDPR export/delete by user
"""

import gc
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_repository")
class TestLangGraphExecutionTraceRepositoryABC:
    """Tests for LangGraphExecutionTraceRepositoryBase abstract base class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_abc_defines_create_method(self) -> None:
        """ABC should define create method."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        assert hasattr(LangGraphExecutionTraceRepositoryBase, "create")

    def test_abc_defines_create_batch_method(self) -> None:
        """ABC should define create_batch method."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        assert hasattr(LangGraphExecutionTraceRepositoryBase, "create_batch")

    def test_abc_defines_get_by_session_method(self) -> None:
        """ABC should define get_by_session method."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        assert hasattr(LangGraphExecutionTraceRepositoryBase, "get_by_session")

    def test_abc_defines_get_by_user_method(self) -> None:
        """ABC should define get_by_user method for GDPR export."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        assert hasattr(LangGraphExecutionTraceRepositoryBase, "get_by_user")

    def test_abc_defines_delete_by_user_method(self) -> None:
        """ABC should define delete_by_user method for GDPR deletion."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        assert hasattr(LangGraphExecutionTraceRepositoryBase, "delete_by_user")

    def test_abc_cannot_be_instantiated(self) -> None:
        """ABC should not be directly instantiable."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
        )

        with pytest.raises(TypeError):
            LangGraphExecutionTraceRepositoryBase()  # type: ignore[abstract]


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_repository")
class TestPostgresLangGraphExecutionTraceRepository:
    """Tests for PostgresLangGraphExecutionTraceRepository concrete implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inherits_from_abc(self) -> None:
        """PostgresLangGraphExecutionTraceRepository should inherit from ABC."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            LangGraphExecutionTraceRepositoryBase,
            PostgresLangGraphExecutionTraceRepository,
        )

        assert issubclass(
            PostgresLangGraphExecutionTraceRepository,
            LangGraphExecutionTraceRepositoryBase,
        )

    def test_accepts_session_factory(self) -> None:
        """Repository should accept a session factory."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        mock_factory = AsyncMock(return_value=None)
        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)
        assert repo._session_factory is mock_factory

    @pytest.mark.asyncio
    async def test_create_returns_trace_id(self) -> None:
        """create() should return the trace_id."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        # Create mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.add = MagicMock()

        # Create async context manager factory
        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        trace_data = {
            "trace_id": "trace-exec-123",
            "session_id": "session-456",
            "run_id": "run-xyz",
            "user_id": "user:alice",
            "organization_id": "org:acme",
            "node_name": "router",
            "status": "completed",
            "start_time": 1704720000000,  # epoch ms
            "end_time": 1704720001000,
            "duration_ms": 1000,
            "sequence_number": 0,
            "created_at": datetime.now(UTC),
        }

        result = await repo.create(trace_data)

        assert result == "trace-exec-123"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_batch_returns_count(self) -> None:
        """create_batch() should return count of inserted traces."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.add_all = MagicMock()

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        traces = [
            {
                "trace_id": f"trace-exec-{i}",
                "session_id": "session-456",
                "run_id": "run-xyz",
                "user_id": "user:alice",
                "organization_id": "org:acme",
                "node_name": f"node_{i}",
                "status": "completed",
                "start_time": 1704720000000 + i * 1000,
                "sequence_number": i,
                "created_at": datetime.now(UTC),
            }
            for i in range(5)
        ]

        count = await repo.create_batch(traces)

        assert count == 5
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_batch_empty_returns_zero(self) -> None:
        """create_batch() with empty list should return 0."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        mock_factory = AsyncMock(return_value=None)
        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        count = await repo.create_batch([])

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_by_session_returns_traces(self) -> None:
        """get_by_session() should return list of LangGraphExecutionTraceSummary."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )
        from mcp_server_langgraph.storage.models import LangGraphExecutionTraceSummary

        # Mock traces
        mock_traces = [MagicMock() for _ in range(3)]
        for i, t in enumerate(mock_traces):
            t.trace_id = f"trace-exec-{i}"
            t.node_name = f"node_{i}"
            t.status = "completed"
            t.start_time = 1704720000000 + i * 1000
            t.end_time = 1704720000500 + i * 1000
            t.duration_ms = 500
            t.sequence_number = i

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_traces

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        results = await repo.get_by_session("session-456", limit=10, offset=0)

        assert len(results) == 3
        assert all(isinstance(r, LangGraphExecutionTraceSummary) for r in results)
        assert results[0].trace_id == "trace-exec-0"
        assert results[0].node_name == "node_0"
        assert results[0].status == "completed"

    @pytest.mark.asyncio
    async def test_get_by_user_returns_dicts_for_gdpr(self) -> None:
        """get_by_user() should return list of dicts for GDPR export."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        mock_trace = MagicMock()
        mock_trace.to_dict.return_value = {
            "trace_id": "trace-exec-abc",
            "user_id": "user:alice",
            "node_name": "router",
            "status": "completed",
        }

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_trace]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        results = await repo.get_by_user("user:alice")

        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["user_id"] == "user:alice"

    @pytest.mark.asyncio
    async def test_delete_by_user_returns_count(self) -> None:
        """delete_by_user() should return count of deleted traces."""
        from mcp_server_langgraph.repositories.langgraph_execution_trace import (
            PostgresLangGraphExecutionTraceRepository,
        )

        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock(return_value=None)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresLangGraphExecutionTraceRepository(session_factory=mock_factory)

        count = await repo.delete_by_user("user:alice")

        assert count == 5
        mock_session.commit.assert_called_once()


@pytest.mark.xdist_group(name="test_langgraph_execution_trace_repository")
class TestLangGraphExecutionTraceRepositoryExports:
    """Tests for repository module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_class_exported_from_module(self) -> None:
        """LangGraphExecutionTraceRepositoryBase should be exported from module."""
        from mcp_server_langgraph.repositories import langgraph_execution_trace

        assert hasattr(langgraph_execution_trace, "LangGraphExecutionTraceRepositoryBase")

    def test_postgres_class_exported_from_module(self) -> None:
        """PostgresLangGraphExecutionTraceRepository should be exported from module."""
        from mcp_server_langgraph.repositories import langgraph_execution_trace

        assert hasattr(langgraph_execution_trace, "PostgresLangGraphExecutionTraceRepository")
