"""
Unit tests for WebSocket Handlers module __init__.py.

Tests that all handler classes are correctly exported and importable.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_handlers_init"),
]


@pytest.mark.xdist_group(name="websocket_handlers_init")
class TestHandlersModuleExports:
    """Tests for handler module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing AgentRequestHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import AgentRequestHandler

        assert AgentRequestHandler is not None

    def test_alert_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing AlertHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import AlertHandler

        assert AlertHandler is not None

    def test_audit_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing AuditHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import AuditHandler

        assert AuditHandler is not None

    def test_connection_health_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing ConnectionHealthHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import ConnectionHealthHandler

        assert ConnectionHealthHandler is not None

    def test_connections_realtime_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing ConnectionsRealtimeHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import ConnectionsRealtimeHandler

        assert ConnectionsRealtimeHandler is not None

    def test_cost_tracking_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing CostTrackingHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import CostTrackingHandler

        assert CostTrackingHandler is not None

    def test_heart_metrics_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing HeartMetricsHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import HeartMetricsHandler

        assert HeartMetricsHandler is not None

    def test_mcp_websocket_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing MCPWebSocketHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import MCPWebSocketHandler

        assert MCPWebSocketHandler is not None

    def test_mcp_task_websocket_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing MCPTaskWebSocketHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import MCPTaskWebSocketHandler

        assert MCPTaskWebSocketHandler is not None

    def test_notification_websocket_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing NotificationWebSocketHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import NotificationWebSocketHandler

        assert NotificationWebSocketHandler is not None

    def test_workflow_execution_handler_export(self) -> None:
        """GIVEN handlers module WHEN importing WorkflowExecutionHandler THEN succeeds."""
        from mcp_server_langgraph.websocket.handlers import WorkflowExecutionHandler

        assert WorkflowExecutionHandler is not None


@pytest.mark.xdist_group(name="websocket_handlers_init")
class TestHandlersModuleAll:
    """Tests for __all__ export list."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_contains_expected_handlers(self) -> None:
        """GIVEN handlers module WHEN checking __all__ THEN contains all handlers."""
        import mcp_server_langgraph.websocket.handlers as handlers_module

        expected_exports = [
            "AgentRequestHandler",
            "AlertHandler",
            "AuditHandler",
            "ConnectionHealthHandler",
            "ConnectionsRealtimeHandler",
            "CostTrackingHandler",
            "HeartMetricsHandler",
            "MCPTaskWebSocketHandler",
            "MCPWebSocketHandler",
            "NotificationWebSocketHandler",
            "WorkflowExecutionHandler",
        ]

        for export in expected_exports:
            assert export in handlers_module.__all__, f"{export} not in __all__"

    def test_all_exports_are_accessible(self) -> None:
        """GIVEN handlers module WHEN accessing __all__ exports THEN all work."""
        import mcp_server_langgraph.websocket.handlers as handlers_module

        for name in handlers_module.__all__:
            obj = getattr(handlers_module, name)
            assert obj is not None, f"{name} is None"


@pytest.mark.xdist_group(name="websocket_handlers_init")
class TestHandlerClassStructure:
    """Tests for basic handler class structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handlers_are_classes(self) -> None:
        """GIVEN handler exports WHEN checking type THEN all are classes."""
        from mcp_server_langgraph.websocket.handlers import (
            AgentRequestHandler,
            AlertHandler,
            AuditHandler,
            ConnectionHealthHandler,
            ConnectionsRealtimeHandler,
            CostTrackingHandler,
            HeartMetricsHandler,
            MCPTaskWebSocketHandler,
            MCPWebSocketHandler,
            NotificationWebSocketHandler,
            WorkflowExecutionHandler,
        )

        handlers = [
            AgentRequestHandler,
            AlertHandler,
            AuditHandler,
            ConnectionHealthHandler,
            ConnectionsRealtimeHandler,
            CostTrackingHandler,
            HeartMetricsHandler,
            MCPTaskWebSocketHandler,
            MCPWebSocketHandler,
            NotificationWebSocketHandler,
            WorkflowExecutionHandler,
        ]

        for handler_cls in handlers:
            assert isinstance(handler_cls, type), f"{handler_cls} is not a class"

    def test_handlers_have_handle_message_method(self) -> None:
        """GIVEN handler classes WHEN checking for handle_message THEN all have it."""
        from mcp_server_langgraph.websocket.handlers import (
            AgentRequestHandler,
            AlertHandler,
            AuditHandler,
            ConnectionHealthHandler,
            ConnectionsRealtimeHandler,
            CostTrackingHandler,
            HeartMetricsHandler,
            MCPTaskWebSocketHandler,
            MCPWebSocketHandler,
            NotificationWebSocketHandler,
            WorkflowExecutionHandler,
        )

        handlers = [
            AgentRequestHandler,
            AlertHandler,
            AuditHandler,
            ConnectionHealthHandler,
            ConnectionsRealtimeHandler,
            CostTrackingHandler,
            HeartMetricsHandler,
            MCPTaskWebSocketHandler,
            MCPWebSocketHandler,
            NotificationWebSocketHandler,
            WorkflowExecutionHandler,
        ]

        for handler_cls in handlers:
            assert hasattr(
                handler_cls, "handle_message"
            ), f"{handler_cls.__name__} missing handle_message"
            assert callable(
                getattr(handler_cls, "handle_message")
            ), f"{handler_cls.__name__}.handle_message not callable"
