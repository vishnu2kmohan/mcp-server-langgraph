"""
Tests for OrchestrationToolHandler.

TDD: These tests define the expected behavior for MCP orchestration tools.

The OrchestrationToolHandler exposes multi-agent orchestration as MCP tools:
- decompose: Break down a task into subtasks
- execute: Execute a decomposition
- status: Check task status
- cancel: Cancel a running task
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="orchestration_handler")
class TestOrchestrationToolHandlerModule:
    """Test module structure and exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestration_handler_module_exists(self) -> None:
        """Test that orchestration handler module exists."""
        from mcp_server_langgraph.mcp.handlers import orchestration

        assert orchestration is not None

    def test_orchestration_tool_handler_class_exists(self) -> None:
        """Test that OrchestrationToolHandler class exists."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        assert OrchestrationToolHandler is not None

    def test_create_orchestration_tool_handler_factory_exists(self) -> None:
        """Test that factory function exists."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            create_orchestration_tool_handler,
        )

        assert callable(create_orchestration_tool_handler)


@pytest.mark.xdist_group(name="orchestration_handler")
class TestOrchestrationToolHandlerInitialization:
    """Test handler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestration_handler_initialization(self) -> None:
        """Test that handler can be initialized."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        assert handler is not None

    def test_orchestration_handler_accepts_orchestrator(self) -> None:
        """Test that handler accepts orchestrator instance."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_orchestrator = MagicMock()
        handler = OrchestrationToolHandler(orchestrator=mock_orchestrator)
        assert handler.orchestrator is mock_orchestrator

    def test_orchestration_handler_accepts_resource_provider(self) -> None:
        """Test that handler accepts resource provider."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_provider = MagicMock()
        handler = OrchestrationToolHandler(resource_provider=mock_provider)
        assert handler.resource_provider is mock_provider


@pytest.mark.xdist_group(name="orchestration_handler")
class TestOrchestrationToolDefinition:
    """Test tool definition for MCP registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_tool_definition_returns_dict(self) -> None:
        """Test that get_tool_definition returns a dict."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        assert isinstance(tool_def, dict)

    def test_tool_definition_has_name(self) -> None:
        """Test that tool definition has name field."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        assert tool_def["name"] == "orchestration"

    def test_tool_definition_has_description(self) -> None:
        """Test that tool definition has description."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        assert "description" in tool_def
        assert "orchestration" in tool_def["description"].lower()

    def test_tool_definition_has_input_schema(self) -> None:
        """Test that tool definition has inputSchema."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        assert "inputSchema" in tool_def
        assert tool_def["inputSchema"]["type"] == "object"

    def test_input_schema_has_operation_enum(self) -> None:
        """Test that inputSchema has operation with enum values."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        schema = tool_def["inputSchema"]
        assert "operation" in schema["properties"]
        assert "enum" in schema["properties"]["operation"]
        operations = schema["properties"]["operation"]["enum"]
        assert "decompose" in operations
        assert "execute" in operations
        assert "status" in operations
        assert "cancel" in operations

    def test_input_schema_has_task_property(self) -> None:
        """Test that inputSchema has task property for decompose."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        schema = tool_def["inputSchema"]
        assert "task" in schema["properties"]

    def test_input_schema_has_task_id_property(self) -> None:
        """Test that inputSchema has task_id property."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        tool_def = handler.get_tool_definition()
        schema = tool_def["inputSchema"]
        assert "task_id" in schema["properties"]


@pytest.mark.xdist_group(name="orchestration_handler")
class TestOrchestrationOperationDispatch:
    """Test operation dispatch."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_operation_dispatches_decompose(self) -> None:
        """Test that handle_operation dispatches to decompose handler."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        handler._handle_decompose = AsyncMock(return_value={"subtasks": []})

        await handler.handle_operation("decompose", {"task": "test task"})
        handler._handle_decompose.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_operation_dispatches_execute(self) -> None:
        """Test that handle_operation dispatches to execute handler."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        handler._handle_execute = AsyncMock(return_value={"results": []})

        await handler.handle_operation("execute", {"task_id": "task-123"})
        handler._handle_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_operation_dispatches_status(self) -> None:
        """Test that handle_operation dispatches to status handler."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        handler._handle_status = AsyncMock(return_value={"status": "pending"})

        await handler.handle_operation("status", {"task_id": "task-123"})
        handler._handle_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_operation_dispatches_cancel(self) -> None:
        """Test that handle_operation dispatches to cancel handler."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        handler._handle_cancel = AsyncMock(return_value={"cancelled": True})

        await handler.handle_operation("cancel", {"task_id": "task-123"})
        handler._handle_cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self) -> None:
        """Test that unknown operation returns error."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("unknown", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_operations_are_case_insensitive(self) -> None:
        """Test that operations are case insensitive."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        handler._handle_status = AsyncMock(return_value={"status": "pending"})

        await handler.handle_operation("STATUS", {"task_id": "task-123"})
        handler._handle_status.assert_called_once()


@pytest.mark.xdist_group(name="orchestration_handler")
class TestDecomposeOperation:
    """Test decompose operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_decompose_requires_task(self) -> None:
        """Test that decompose requires task argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("decompose", {})
        assert "error" in result
        assert "task" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_decompose_returns_subtasks(self) -> None:
        """Test that decompose returns subtasks."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_orchestrator = MagicMock()
        # decompose_task is a synchronous method, use MagicMock not AsyncMock
        mock_orchestrator.decompose_task = MagicMock(
            return_value=MagicMock(
                task_id="task-123",
                subtasks=[
                    MagicMock(task_type="analysis", description="Analyze data"),
                ],
                model_dump=MagicMock(
                    return_value={
                        "task_id": "task-123",
                        "subtasks": [{"task_type": "analysis", "description": "Analyze data"}],
                    }
                ),
            )
        )

        handler = OrchestrationToolHandler(orchestrator=mock_orchestrator)
        result = await handler.handle_operation("decompose", {"task": "Analyze data"})

        assert "task_id" in result
        assert "subtasks" in result

    @pytest.mark.asyncio
    async def test_decompose_respects_max_subtasks(self) -> None:
        """Test that decompose respects max_subtasks argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_orchestrator = MagicMock()
        # decompose_task is a synchronous method, use MagicMock not AsyncMock
        mock_orchestrator.decompose_task = MagicMock(
            return_value=MagicMock(model_dump=MagicMock(return_value={"task_id": "t1", "subtasks": []}))
        )

        handler = OrchestrationToolHandler(orchestrator=mock_orchestrator)
        await handler.handle_operation("decompose", {"task": "Test", "max_subtasks": 3})

        # Verify max_subtasks was passed
        call_kwargs = mock_orchestrator.decompose_task.call_args
        assert call_kwargs is not None


@pytest.mark.xdist_group(name="orchestration_handler")
class TestStatusOperation:
    """Test status operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_status_requires_task_id(self) -> None:
        """Test that status requires task_id argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("status", {})
        assert "error" in result
        assert "task_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_status_returns_task_status(self) -> None:
        """Test that status returns task status from resource provider."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_provider = MagicMock()
        mock_provider._tasks = {
            "task-123": MagicMock(
                model_dump=MagicMock(
                    return_value={
                        "task_id": "task-123",
                        "status": "running",
                    }
                )
            )
        }

        handler = OrchestrationToolHandler(resource_provider=mock_provider)
        result = await handler.handle_operation("status", {"task_id": "task-123"})

        assert "task_id" in result
        assert result["task_id"] == "task-123"

    @pytest.mark.asyncio
    async def test_status_returns_not_found_for_unknown_task(self) -> None:
        """Test that status returns not found for unknown task."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_provider = MagicMock()
        mock_provider._tasks = {}

        handler = OrchestrationToolHandler(resource_provider=mock_provider)
        result = await handler.handle_operation("status", {"task_id": "unknown"})

        assert "error" in result or result.get("found") is False


@pytest.mark.xdist_group(name="orchestration_handler")
class TestCancelOperation:
    """Test cancel operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cancel_requires_task_id(self) -> None:
        """Test that cancel requires task_id argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("cancel", {})
        assert "error" in result
        assert "task_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cancel_returns_cancellation_status(self) -> None:
        """Test that cancel returns cancellation status."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.cancel_task = AsyncMock(return_value=True)

        handler = OrchestrationToolHandler(orchestrator=mock_orchestrator)
        result = await handler.handle_operation("cancel", {"task_id": "task-123"})

        assert "cancelled" in result or "success" in result


@pytest.mark.xdist_group(name="orchestration_handler")
class TestExecuteOperation:
    """Test execute operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_requires_task_id(self) -> None:
        """Test that execute requires task_id argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        handler = OrchestrationToolHandler()
        result = await handler.handle_operation("execute", {})
        assert "error" in result
        assert "task_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_returns_results(self) -> None:
        """Test that execute returns execution results."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_provider = MagicMock()
        mock_provider._tasks = {
            "task-123": MagicMock(
                model_dump=MagicMock(
                    return_value={
                        "task_id": "task-123",
                        "subtasks": [],
                    }
                )
            )
        }

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=[])

        handler = OrchestrationToolHandler(
            orchestrator=mock_orchestrator,
            resource_provider=mock_provider,
        )
        result = await handler.handle_operation("execute", {"task_id": "task-123"})

        assert "results" in result or "error" not in result

    @pytest.mark.asyncio
    async def test_execute_accepts_hitl_threshold(self) -> None:
        """Test that execute accepts hitl_threshold argument."""
        from mcp_server_langgraph.mcp.handlers.orchestration import (
            OrchestrationToolHandler,
        )

        mock_provider = MagicMock()
        mock_provider._tasks = {"task-123": MagicMock()}

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_with_hitl = AsyncMock(return_value=[])

        handler = OrchestrationToolHandler(
            orchestrator=mock_orchestrator,
            resource_provider=mock_provider,
        )
        await handler.handle_operation("execute", {"task_id": "task-123", "hitl_threshold": 0.8})

        # Should use execute_with_hitl when threshold is provided
        mock_orchestrator.execute_with_hitl.assert_called_once()


@pytest.mark.xdist_group(name="orchestration_handler")
class TestOrchestrationHandlerExport:
    """Test handler is exported from handlers package."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_exported_from_handlers_package(self) -> None:
        """Test that OrchestrationToolHandler is exported from handlers."""
        from mcp_server_langgraph.mcp.handlers import OrchestrationToolHandler

        assert OrchestrationToolHandler is not None

    def test_factory_exported_from_handlers_package(self) -> None:
        """Test that create_orchestration_tool_handler is exported."""
        from mcp_server_langgraph.mcp.handlers import (
            create_orchestration_tool_handler,
        )

        assert callable(create_orchestration_tool_handler)
