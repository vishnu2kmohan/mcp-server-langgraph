"""
LangGraph Execution Manager Tests (TDD)

Tests for the LangGraphExecutionManager that integrates
workflow storage with the WebSocket execution endpoint.
"""

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.storage.workflow.models import StoredWorkflow


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.xdist_group(name="langgraph_execution_manager"),
]


@pytest.fixture
def mock_workflow_storage() -> AsyncMock:
    """Create a mock workflow storage."""
    storage = AsyncMock()  # async-mock-configured
    storage.get_workflow = AsyncMock(
        return_value=StoredWorkflow(
            id="wf-123",
            name="Test Workflow",
            description="A test workflow",
            nodes=[
                {"id": "start", "type": "start", "data": {}},
                {"id": "llm", "type": "llm", "data": {"model": "gpt-4"}},
                {"id": "end", "type": "end", "data": {}},
            ],
            edges=[
                {"source": "start", "target": "llm"},
                {"source": "llm", "target": "end"},
            ],
            user_id="user-123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    return storage


class TestLangGraphExecutionManager:
    """Tests for LangGraphExecutionManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_workflow_returns_dict(self, mock_workflow_storage: AsyncMock) -> None:
        """get_workflow should return workflow as dict."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        result = await manager.get_workflow("wf-123")

        assert result is not None
        assert result["id"] == "wf-123"
        assert result["name"] == "Test Workflow"
        mock_workflow_storage.get_workflow.assert_called_once_with("wf-123")

    @pytest.mark.asyncio
    async def test_get_workflow_returns_none_for_missing(self, mock_workflow_storage: AsyncMock) -> None:
        """get_workflow should return None for non-existent workflow."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        mock_workflow_storage.get_workflow.return_value = None
        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        result = await manager.get_workflow("missing-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_start_execution_returns_execution_id(self, mock_workflow_storage: AsyncMock) -> None:
        """start_execution should return a unique execution ID."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        execution_id = await manager.start_execution("wf-123")

        assert execution_id is not None
        assert isinstance(execution_id, str)
        assert len(execution_id) > 0

    @pytest.mark.asyncio
    async def test_start_execution_stores_execution_state(self, mock_workflow_storage: AsyncMock) -> None:
        """start_execution should track the running execution."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        execution_id = await manager.start_execution("wf-123", {"prompt": "test"})

        assert manager.is_execution_running("wf-123")
        assert manager.get_execution_id("wf-123") == execution_id

    @pytest.mark.asyncio
    async def test_start_execution_with_input_data(self, mock_workflow_storage: AsyncMock) -> None:
        """start_execution should accept input data."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        input_data = {"prompt": "Hello, world!", "context": []}
        execution_id = await manager.start_execution("wf-123", input_data)

        assert execution_id is not None
        assert manager.get_execution_input("wf-123") == input_data

    @pytest.mark.asyncio
    async def test_stop_execution_returns_true_for_running(self, mock_workflow_storage: AsyncMock) -> None:
        """stop_execution should return True for running execution."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        await manager.start_execution("wf-123")
        result = await manager.stop_execution("wf-123")

        assert result is True
        assert not manager.is_execution_running("wf-123")

    @pytest.mark.asyncio
    async def test_stop_execution_returns_false_for_not_running(self, mock_workflow_storage: AsyncMock) -> None:
        """stop_execution should return False if no execution running."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)
        result = await manager.stop_execution("wf-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_workflows_tracked_separately(self, mock_workflow_storage: AsyncMock) -> None:
        """Manager should track multiple workflows independently."""
        from mcp_server_langgraph.execution.langgraph_manager import (
            LangGraphExecutionManager,
        )

        manager = LangGraphExecutionManager(workflow_storage=mock_workflow_storage)

        exec1 = await manager.start_execution("wf-1")
        exec2 = await manager.start_execution("wf-2")

        assert exec1 != exec2
        assert manager.is_execution_running("wf-1")
        assert manager.is_execution_running("wf-2")

        await manager.stop_execution("wf-1")
        assert not manager.is_execution_running("wf-1")
        assert manager.is_execution_running("wf-2")
