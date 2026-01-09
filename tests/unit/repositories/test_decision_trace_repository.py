"""
Unit tests for DecisionTraceRepository.

TDD RED Phase: Tests for ABC and Postgres implementation of decision trace repository.

Tests:
- ABC interface methods defined
- PostgresDecisionTraceRepository CRUD operations
- Batch insert
- Query by session
- GDPR export/delete by user
- Retention cleanup
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_trace_repository")
class TestDecisionTraceRepositoryABC:
    """Tests for DecisionTraceRepository abstract base class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_abc_defines_create_method(self) -> None:
        """ABC should define create method."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "create")

    def test_abc_defines_create_batch_method(self) -> None:
        """ABC should define create_batch method."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "create_batch")

    def test_abc_defines_get_by_id_method(self) -> None:
        """ABC should define get_by_id method."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "get_by_id")

    def test_abc_defines_get_by_session_method(self) -> None:
        """ABC should define get_by_session method."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "get_by_session")

    def test_abc_defines_get_by_user_method(self) -> None:
        """ABC should define get_by_user method for GDPR export."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "get_by_user")

    def test_abc_defines_delete_by_user_method(self) -> None:
        """ABC should define delete_by_user method for GDPR deletion."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "delete_by_user")

    def test_abc_defines_delete_expired_method(self) -> None:
        """ABC should define delete_expired method for retention."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        assert hasattr(DecisionTraceRepositoryBase, "delete_expired")

    def test_abc_cannot_be_instantiated(self) -> None:
        """ABC should not be directly instantiable."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
        )

        with pytest.raises(TypeError):
            DecisionTraceRepositoryBase()  # type: ignore[abstract]


@pytest.mark.xdist_group(name="test_decision_trace_repository")
class TestPostgresDecisionTraceRepository:
    """Tests for PostgresDecisionTraceRepository concrete implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_inherits_from_abc(self) -> None:
        """PostgresDecisionTraceRepository should inherit from ABC."""
        from mcp_server_langgraph.repositories.decision_trace import (
            DecisionTraceRepositoryBase,
            PostgresDecisionTraceRepository,
        )

        assert issubclass(PostgresDecisionTraceRepository, DecisionTraceRepositoryBase)

    def test_accepts_session_factory(self) -> None:
        """Repository should accept a session factory."""
        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_factory = AsyncMock()
        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)
        assert repo._session_factory is mock_factory

    @pytest.mark.asyncio
    async def test_create_returns_trace_id(self) -> None:
        """create() should return the trace_id."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        # Create mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        # Create async context manager factory
        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        trace_data = {
            "trace_id": "trace-abc123",
            "run_id": "run-xyz",
            "session_id": "session-456",
            "organization_id": "org:acme",
            "user_id": "user:alice",
            "timestamp": datetime.now(UTC),
            "decision_type": "routing",
            "decision_stage": "action",
            "query_text": "How do I deploy?",
            "chosen_action": "call_deploy_tool",
            "confidence": 0.95,
            "rationale": "User wants deployment",
        }

        result = await repo.create(trace_data)

        assert result == "trace-abc123"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_batch_returns_count(self) -> None:
        """create_batch() should return count of inserted traces."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.add_all = MagicMock()

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        traces = [
            {
                "trace_id": f"trace-{i}",
                "run_id": "run-xyz",
                "session_id": "session-456",
                "organization_id": "org:acme",
                "user_id": "user:alice",
                "timestamp": datetime.now(UTC),
                "decision_type": "routing",
                "decision_stage": "action",
                "query_text": f"Query {i}",
                "chosen_action": f"action_{i}",
                "confidence": 0.9,
                "rationale": f"Rationale {i}",
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
        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_factory = AsyncMock()
        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        count = await repo.create_batch([])

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_by_id_returns_trace(self) -> None:
        """get_by_id() should return DecisionTraceRead model."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )
        from mcp_server_langgraph.storage.models import DecisionTraceRead

        # Mock trace object
        mock_trace = MagicMock()
        mock_trace.trace_id = "trace-abc123"
        mock_trace.run_id = "run-xyz"
        mock_trace.session_id = "session-456"
        mock_trace.workflow_id = None
        mock_trace.project_id = None
        mock_trace.timestamp = datetime(2026, 1, 8, 12, 0, 0, tzinfo=UTC)
        mock_trace.decision_type = "routing"
        mock_trace.decision_stage = "action"
        mock_trace.chosen_action = "deploy_tool"
        mock_trace.confidence = 0.95
        mock_trace.rationale = "User wants deployment"
        mock_trace.outcome = "success"
        mock_trace.requires_approval = False
        mock_trace.approval_status = None

        # Mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_trace

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        result = await repo.get_by_id("trace-abc123")

        assert result is not None
        assert isinstance(result, DecisionTraceRead)
        assert result.trace_id == "trace-abc123"
        assert result.decision_type == "routing"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found_returns_none(self) -> None:
        """get_by_id() should return None if not found."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        result = await repo.get_by_id("nonexistent-trace")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_session_returns_summaries(self) -> None:
        """get_by_session() should return list of DecisionTraceSummary."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )
        from mcp_server_langgraph.storage.models import DecisionTraceSummary

        # Mock traces
        mock_traces = [MagicMock() for _ in range(3)]
        for i, t in enumerate(mock_traces):
            t.trace_id = f"trace-{i}"
            t.timestamp = datetime(2026, 1, 8, 12, i, 0, tzinfo=UTC)
            t.decision_type = "routing"
            t.chosen_action = f"action_{i}"
            t.confidence = 0.9
            t.outcome = "success"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_traces

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        results = await repo.get_by_session("session-456", limit=10, offset=0)

        assert len(results) == 3
        assert all(isinstance(r, DecisionTraceSummary) for r in results)
        assert results[0].trace_id == "trace-0"

    @pytest.mark.asyncio
    async def test_get_by_user_returns_dicts_for_gdpr(self) -> None:
        """get_by_user() should return list of dicts for GDPR export."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_trace = MagicMock()
        mock_trace.to_dict.return_value = {
            "trace_id": "trace-abc",
            "user_id": "user:alice",
            "decision_type": "routing",
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

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        results = await repo.get_by_user("user:alice")

        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["user_id"] == "user:alice"

    @pytest.mark.asyncio
    async def test_delete_by_user_returns_count(self) -> None:
        """delete_by_user() should return count of deleted traces."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        count = await repo.delete_by_user("user:alice")

        assert count == 5
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_expired_returns_count(self) -> None:
        """delete_expired() should return count of deleted traces."""
        from contextlib import asynccontextmanager

        from mcp_server_langgraph.repositories.decision_trace import (
            PostgresDecisionTraceRepository,
        )

        mock_result = MagicMock()
        mock_result.rowcount = 100

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        @asynccontextmanager
        async def mock_factory():
            yield mock_session

        repo = PostgresDecisionTraceRepository(session_factory=mock_factory)

        count = await repo.delete_expired(retention_days=90)

        assert count == 100
        mock_session.commit.assert_called_once()


@pytest.mark.xdist_group(name="test_decision_trace_repository")
class TestDecisionTraceRepositoryExports:
    """Tests for repository module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_class_exported_from_module(self) -> None:
        """DecisionTraceRepositoryBase should be exported from module."""
        from mcp_server_langgraph.repositories import decision_trace

        assert hasattr(decision_trace, "DecisionTraceRepositoryBase")

    def test_postgres_class_exported_from_module(self) -> None:
        """PostgresDecisionTraceRepository should be exported from module."""
        from mcp_server_langgraph.repositories import decision_trace

        assert hasattr(decision_trace, "PostgresDecisionTraceRepository")
