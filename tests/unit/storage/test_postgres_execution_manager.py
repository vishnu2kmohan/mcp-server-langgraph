"""
Unit tests for PostgresExecutionHistoryManager

TDD tests for database-backed execution history storage.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.api.v1.workflow_executions import ExecutionHistoryManagerInterface

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_session():
    """Create mock SQLAlchemy async session.

    These mocks are intentionally unconfigured here as individual tests
    configure the return_value or side_effect as needed.
    """
    mock = AsyncMock()  # noqa: async-mock-config
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()  # noqa: async-mock-config
    mock.execute = AsyncMock()  # noqa: async-mock-config
    mock.commit = AsyncMock()  # noqa: async-mock-config
    mock.rollback = AsyncMock()  # noqa: async-mock-config
    mock.add = MagicMock()
    return mock


@pytest.fixture
def mock_session_maker(mock_session):
    """Create mock async session maker."""

    def _maker():
        return mock_session

    return _maker


@pytest.fixture
def mock_engine():
    """Create mock async engine."""
    return MagicMock()


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerInterface:
    """Tests for PostgresExecutionHistoryManager interface compliance."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_manager_implements_interface(self, mock_engine):
        """Test that PostgresExecutionHistoryManager implements the interface."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        assert isinstance(manager, ExecutionHistoryManagerInterface)


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerGetWorkflow:
    """Tests for get_workflow method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_workflow_returns_workflow_when_exists(self, mock_engine, mock_session_maker, mock_session):
        """Test get_workflow returns workflow data when found."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        # Mock query result - note: 'name' is a special MagicMock param,
        # so we need to set it as an attribute after creation
        mock_workflow = MagicMock()
        mock_workflow.id = "wf-1"
        mock_workflow.name = "Test Workflow"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.get_workflow("wf-1")

        assert result is not None
        assert result["id"] == "wf-1"
        assert result["name"] == "Test Workflow"

    @pytest.mark.asyncio
    async def test_get_workflow_returns_none_when_not_found(self, mock_engine, mock_session_maker, mock_session):
        """Test get_workflow returns None when workflow not found."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.get_workflow("nonexistent")

        assert result is None


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerListExecutions:
    """Tests for list_executions method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_executions_returns_empty_list_when_none(self, mock_engine, mock_session_maker, mock_session):
        """Test list_executions returns empty list when no executions."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.list_executions(workflow_id="wf-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_executions_returns_execution_dicts(self, mock_engine, mock_session_maker, mock_session):
        """Test list_executions returns list of execution dictionaries."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        now = datetime.now(UTC)
        mock_executions = [
            MagicMock(
                id="exec-1",
                workflow_id="wf-1",
                status="completed",
                started_at=now,
                completed_at=now,
                input_data={"query": "test"},
                output_data={"result": "success"},
                error=None,
            ),
            MagicMock(
                id="exec-2",
                workflow_id="wf-1",
                status="running",
                started_at=now,
                completed_at=None,
                input_data={},
                output_data=None,
                error=None,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_executions
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.list_executions(workflow_id="wf-1")

        assert len(result) == 2
        assert result[0]["id"] == "exec-1"
        assert result[0]["status"] == "completed"
        assert result[1]["id"] == "exec-2"
        assert result[1]["status"] == "running"

    @pytest.mark.asyncio
    async def test_list_executions_filters_by_status(self, mock_engine, mock_session_maker, mock_session):
        """Test list_executions applies status filter."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        await manager.list_executions(workflow_id="wf-1", status="failed")

        # Verify execute was called (we can't easily check the query content)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_executions_applies_limit(self, mock_engine, mock_session_maker, mock_session):
        """Test list_executions applies limit parameter."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        await manager.list_executions(workflow_id="wf-1", limit=10)

        mock_session.execute.assert_called_once()


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerGetExecution:
    """Tests for get_execution method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_execution_returns_execution_when_found(self, mock_engine, mock_session_maker, mock_session):
        """Test get_execution returns execution when found."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        now = datetime.now(UTC)
        mock_execution = MagicMock(
            id="exec-1",
            workflow_id="wf-1",
            status="completed",
            started_at=now,
            completed_at=now,
            input_data={"query": "test"},
            output_data={"result": "success"},
            error=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.get_execution(workflow_id="wf-1", execution_id="exec-1")

        assert result is not None
        assert result["id"] == "exec-1"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_execution_returns_none_when_not_found(self, mock_engine, mock_session_maker, mock_session):
        """Test get_execution returns None when not found."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.get_execution(workflow_id="wf-1", execution_id="nonexistent")

        assert result is None


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerCreateExecution:
    """Tests for create_execution method (additional functionality)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_execution_stores_and_returns_id(self, mock_engine, mock_session_maker, mock_session):
        """Test create_execution creates and returns execution ID."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        result = await manager.create_execution(
            workflow_id="wf-1",
            input_data={"query": "test"},
        )

        assert result is not None
        assert isinstance(result, str)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.xdist_group(name="postgres_execution_manager")
class TestPostgresExecutionHistoryManagerUpdateExecution:
    """Tests for update_execution method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_execution_updates_status(self, mock_engine, mock_session_maker, mock_session):
        """Test update_execution updates status."""
        from mcp_server_langgraph.storage.workflow.postgres_execution_manager import (
            PostgresExecutionHistoryManager,
        )

        mock_execution = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution
        mock_session.execute.return_value = mock_result

        manager = PostgresExecutionHistoryManager(engine=mock_engine)
        manager._session_maker = mock_session_maker

        await manager.update_execution(
            execution_id="exec-1",
            status="completed",
            output_data={"result": "success"},
        )

        mock_session.commit.assert_called_once()
        assert mock_execution.status == "completed"
