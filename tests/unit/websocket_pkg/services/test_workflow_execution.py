"""Unit tests for WebSocket WorkflowExecutionServiceAdapter.

Tests the WorkflowExecutionServiceAdapter that wraps workflow execution
for WebSocket handlers.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level marker for test discovery
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_workflow_execution")
class TestWorkflowExecutionServiceAdapter:
    """Test suite for WorkflowExecutionServiceAdapter."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            reset_websocket_execution_service,
        )

        reset_websocket_execution_service()
        gc.collect()

    def test_init_without_execution_manager(self) -> None:
        """Test adapter initialization without execution manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()

        assert adapter._execution_manager is None
        assert adapter._active_executions == {}

    def test_init_with_execution_manager(self) -> None:
        """Test adapter initialization with execution manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = MagicMock()
        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)

        assert adapter._execution_manager is mock_manager

    def test_has_real_manager_true_when_manager_set(self) -> None:
        """Test has_real_manager returns True when manager is set."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = MagicMock()
        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)

        assert adapter.has_real_manager is True

    def test_has_real_manager_false_when_no_manager(self) -> None:
        """Test has_real_manager returns False when no manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()

        assert adapter.has_real_manager is False

    @pytest.mark.asyncio
    async def test_get_workflow_with_real_manager(self) -> None:
        """Test get_workflow uses real manager when available."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "nodes": ["node1", "node2"],
                "status": "active",
            }
        )

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.get_workflow("wf-123")

        assert result is not None
        assert result["id"] == "wf-123"
        assert result["name"] == "Test Workflow"
        mock_manager.get_workflow.assert_awaited_once_with("wf-123")

    @pytest.mark.asyncio
    async def test_get_workflow_returns_stub_without_manager(self) -> None:
        """Test get_workflow returns stub data without manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()
        result = await adapter.get_workflow("wf-456")

        assert result is not None
        assert result["id"] == "wf-456"
        assert result["name"] == "Workflow wf-456"
        assert result["nodes"] == []
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_get_workflow_handles_manager_error(self) -> None:
        """Test get_workflow falls back to stub on manager error."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.get_workflow = AsyncMock(side_effect=Exception("DB error"))

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.get_workflow("wf-error")

        # Should fall back to stub
        assert result is not None
        assert result["id"] == "wf-error"
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_start_execution_with_real_manager(self) -> None:
        """Test start_execution uses real manager when available."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.create_execution = AsyncMock(return_value="exec-real-123")

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.start_execution("wf-1", input_data={"key": "value"})

        assert result == "exec-real-123"
        mock_manager.create_execution.assert_awaited_once_with(
            workflow_id="wf-1",
            input_data={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_start_execution_without_manager(self) -> None:
        """Test start_execution creates stub execution without manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()
        result = await adapter.start_execution("wf-stub")

        assert result.startswith("exec-wf-stub-")
        assert len(result) == len("exec-wf-stub-") + 8  # 8 hex chars
        assert "wf-stub" in adapter._active_executions
        assert adapter._active_executions["wf-stub"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_start_execution_with_input_data(self) -> None:
        """Test start_execution stores input data in local state."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()
        input_data = {"prompt": "Hello", "max_tokens": 100}

        await adapter.start_execution("wf-input", input_data=input_data)

        assert adapter._active_executions["wf-input"]["input_data"] == input_data

    @pytest.mark.asyncio
    async def test_start_execution_handles_manager_error(self) -> None:
        """Test start_execution falls back to stub on manager error."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.create_execution = AsyncMock(side_effect=Exception("Failed"))

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.start_execution("wf-fallback")

        # Should fall back to stub execution
        assert result.startswith("exec-wf-fallback-")
        assert "wf-fallback" in adapter._active_executions

    @pytest.mark.asyncio
    async def test_stop_execution_with_real_manager(self) -> None:
        """Test stop_execution uses real manager when available."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.update_execution = AsyncMock()  # noqa: async-mock-config

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.stop_execution("wf-stop")

        assert result is True
        mock_manager.update_execution.assert_awaited_once_with(
            execution_id="wf-stop",
            status="stopped",
        )

    @pytest.mark.asyncio
    async def test_stop_execution_updates_local_state(self) -> None:
        """Test stop_execution updates local state without manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()
        adapter._active_executions["wf-running"] = {
            "id": "exec-1",
            "workflow_id": "wf-running",
            "status": "running",
        }

        result = await adapter.stop_execution("wf-running")

        assert result is True
        assert adapter._active_executions["wf-running"]["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_stop_execution_returns_false_for_unknown(self) -> None:
        """Test stop_execution returns False for unknown workflow."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()

        result = await adapter.stop_execution("wf-unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_execution_handles_manager_error(self) -> None:
        """Test stop_execution handles manager error gracefully."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.update_execution = AsyncMock(side_effect=Exception("Error"))

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)

        # Without local state, should return False after manager error
        result = await adapter.stop_execution("wf-error")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_execution_status_with_real_manager(self) -> None:
        """Test get_execution_status uses real manager when available."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.list_executions = AsyncMock(
            return_value=[
                {"id": "exec-1", "workflow_id": "wf-1", "status": "running"},
            ]
        )

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.get_execution_status("wf-1")

        assert result is not None
        assert result["id"] == "exec-1"
        assert result["status"] == "running"
        mock_manager.list_executions.assert_awaited_once_with(
            workflow_id="wf-1",
            limit=1,
        )

    @pytest.mark.asyncio
    async def test_get_execution_status_returns_none_when_no_executions(self) -> None:
        """Test get_execution_status returns None when no executions found."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.list_executions = AsyncMock(return_value=[])

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.get_execution_status("wf-empty")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_execution_status_from_local_state(self) -> None:
        """Test get_execution_status returns local state without manager."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()
        adapter._active_executions["wf-local"] = {
            "id": "exec-local",
            "workflow_id": "wf-local",
            "status": "completed",
        }

        result = await adapter.get_execution_status("wf-local")

        assert result is not None
        assert result["id"] == "exec-local"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_execution_status_returns_idle_for_unknown(self) -> None:
        """Test get_execution_status returns idle status for unknown workflow."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        adapter = WorkflowExecutionServiceAdapter()

        result = await adapter.get_execution_status("wf-unknown")

        assert result is not None
        assert result["id"] is None
        assert result["workflow_id"] == "wf-unknown"
        assert result["status"] == "idle"

    @pytest.mark.asyncio
    async def test_get_execution_status_handles_manager_error(self) -> None:
        """Test get_execution_status falls back on manager error."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            WorkflowExecutionServiceAdapter,
        )

        mock_manager = AsyncMock()  # noqa: async-mock-config
        mock_manager.list_executions = AsyncMock(side_effect=Exception("DB error"))

        adapter = WorkflowExecutionServiceAdapter(execution_manager=mock_manager)
        result = await adapter.get_execution_status("wf-error")

        # Should fall back to idle status
        assert result is not None
        assert result["status"] == "idle"


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_workflow_execution")
class TestWorkflowExecutionSingleton:
    """Test suite for workflow execution service singleton functions."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            reset_websocket_execution_service,
        )

        reset_websocket_execution_service()
        gc.collect()

    def test_get_websocket_execution_service_creates_singleton(self) -> None:
        """Test get_websocket_execution_service creates singleton instance."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            get_websocket_execution_service,
            WorkflowExecutionServiceAdapter,
        )

        with patch("mcp_server_langgraph.websocket.services.workflow_execution.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            result = get_websocket_execution_service()

            assert isinstance(result, WorkflowExecutionServiceAdapter)

    def test_get_websocket_execution_service_returns_same_instance(self) -> None:
        """Test get_websocket_execution_service returns same instance."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            get_websocket_execution_service,
        )

        with patch("mcp_server_langgraph.websocket.services.workflow_execution.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            result1 = get_websocket_execution_service()
            result2 = get_websocket_execution_service()

            assert result1 is result2

    def test_reset_websocket_execution_service_clears_singleton(self) -> None:
        """Test reset_websocket_execution_service clears singleton."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            get_websocket_execution_service,
            reset_websocket_execution_service,
        )

        with patch("mcp_server_langgraph.websocket.services.workflow_execution.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            first = get_websocket_execution_service()
            reset_websocket_execution_service()
            second = get_websocket_execution_service()

            assert first is not second

    def test_get_websocket_execution_service_with_real_manager(self) -> None:
        """Test get_websocket_execution_service gets real manager when enabled."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            get_websocket_execution_service,
        )

        mock_manager = MagicMock()

        with (
            patch("mcp_server_langgraph.websocket.services.workflow_execution.get_feature_flags") as mock_flags,
            patch(
                "mcp_server_langgraph.storage.workflow.postgres_execution_manager.get_execution_manager"
            ) as mock_get_manager,
        ):
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff
            mock_get_manager.return_value = mock_manager

            result = get_websocket_execution_service()

            assert result.has_real_manager is True

    def test_get_websocket_execution_service_handles_exception(self) -> None:
        """Test get_websocket_execution_service handles exceptions gracefully."""
        from mcp_server_langgraph.websocket.services.workflow_execution import (
            get_websocket_execution_service,
        )

        with patch("mcp_server_langgraph.websocket.services.workflow_execution.get_feature_flags") as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            # Patch the import location to raise an exception
            with patch(
                "mcp_server_langgraph.storage.workflow.postgres_execution_manager.get_execution_manager",
                side_effect=Exception("Connection failed"),
            ):
                result = get_websocket_execution_service()

                # Should still work, just without real manager
                assert result.has_real_manager is False
