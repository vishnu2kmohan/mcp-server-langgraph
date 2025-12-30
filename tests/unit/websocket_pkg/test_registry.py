"""
Unit tests for WebSocket Broadcaster Registry.

Tests the registry module which manages broadcaster singleton instances
for WebSocket endpoints.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_registry"),
]


@pytest.mark.xdist_group(name="websocket_registry")
class TestNotificationBroadcaster:
    """Tests for notification broadcaster registry functions."""

    def teardown_method(self) -> None:
        """Force GC and reset global state to prevent mock accumulation."""
        gc.collect()
        # Reset global state
        from mcp_server_langgraph.websocket import registry

        registry._notification_broadcaster = None

    def test_get_notification_broadcaster_creates_instance(self) -> None:
        """GIVEN no broadcaster exists WHEN getting broadcaster THEN creates one."""
        from mcp_server_langgraph.websocket import registry

        # Reset to ensure clean state
        registry._notification_broadcaster = None

        with patch("mcp_server_langgraph.notifications.broadcast.NotificationBroadcaster") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            result = registry.get_notification_broadcaster()

        assert result == mock_instance
        mock_class.assert_called_once()

    def test_get_notification_broadcaster_returns_singleton(self) -> None:
        """GIVEN broadcaster exists WHEN getting broadcaster THEN returns same instance."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry._notification_broadcaster = mock_instance

        result = registry.get_notification_broadcaster()

        assert result is mock_instance

    def test_set_notification_broadcaster_overrides_instance(self) -> None:
        """GIVEN broadcaster exists WHEN setting new broadcaster THEN overrides it."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry.set_notification_broadcaster(mock_instance)

        assert registry._notification_broadcaster is mock_instance

    def test_set_notification_broadcaster_clears_with_none(self) -> None:
        """GIVEN broadcaster exists WHEN setting None THEN clears it."""
        from mcp_server_langgraph.websocket import registry

        registry._notification_broadcaster = MagicMock()
        registry.set_notification_broadcaster(None)

        assert registry._notification_broadcaster is None


@pytest.mark.xdist_group(name="websocket_registry")
class TestAlertBroadcaster:
    """Tests for alert broadcaster registry functions."""

    def teardown_method(self) -> None:
        """Force GC and reset global state to prevent mock accumulation."""
        gc.collect()
        from mcp_server_langgraph.websocket import registry

        registry._alert_broadcaster = None

    def test_get_alert_broadcaster_creates_instance(self) -> None:
        """GIVEN no broadcaster exists WHEN getting broadcaster THEN creates one."""
        from mcp_server_langgraph.websocket import registry

        registry._alert_broadcaster = None

        with patch("mcp_server_langgraph.alerts.broadcaster.AlertBroadcaster") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            result = registry.get_alert_broadcaster()

        assert result == mock_instance
        mock_class.assert_called_once()

    def test_get_alert_broadcaster_returns_singleton(self) -> None:
        """GIVEN broadcaster exists WHEN getting broadcaster THEN returns same instance."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry._alert_broadcaster = mock_instance

        result = registry.get_alert_broadcaster()

        assert result is mock_instance

    def test_set_alert_broadcaster_overrides_instance(self) -> None:
        """GIVEN broadcaster exists WHEN setting new broadcaster THEN overrides it."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry.set_alert_broadcaster(mock_instance)

        assert registry._alert_broadcaster is mock_instance


@pytest.mark.xdist_group(name="websocket_registry")
class TestAuditEventBroadcaster:
    """Tests for audit event broadcaster registry functions."""

    def teardown_method(self) -> None:
        """Force GC and reset global state to prevent mock accumulation."""
        gc.collect()
        from mcp_server_langgraph.websocket import registry

        registry._audit_broadcaster = None

    def test_get_audit_event_broadcaster_creates_instance(self) -> None:
        """GIVEN no broadcaster exists WHEN getting broadcaster THEN creates one."""
        from mcp_server_langgraph.websocket import registry

        registry._audit_broadcaster = None

        with patch("mcp_server_langgraph.audit.broadcast.AuditEventBroadcaster") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            result = registry.get_audit_event_broadcaster()

        assert result == mock_instance
        mock_class.assert_called_once()

    def test_get_audit_event_broadcaster_returns_singleton(self) -> None:
        """GIVEN broadcaster exists WHEN getting broadcaster THEN returns same instance."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry._audit_broadcaster = mock_instance

        result = registry.get_audit_event_broadcaster()

        assert result is mock_instance

    def test_set_audit_event_broadcaster_overrides_instance(self) -> None:
        """GIVEN broadcaster exists WHEN setting new broadcaster THEN overrides it."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry.set_audit_event_broadcaster(mock_instance)

        assert registry._audit_broadcaster is mock_instance


@pytest.mark.xdist_group(name="websocket_registry")
class TestAgentRequestBroadcaster:
    """Tests for agent request (HITL) broadcaster registry functions."""

    def teardown_method(self) -> None:
        """Force GC and reset global state to prevent mock accumulation."""
        gc.collect()
        from mcp_server_langgraph.websocket import registry

        registry._agent_request_broadcaster = None

    def test_get_agent_request_broadcaster_creates_instance(self) -> None:
        """GIVEN no broadcaster exists WHEN getting broadcaster THEN creates one."""
        from mcp_server_langgraph.websocket import registry

        registry._agent_request_broadcaster = None

        with patch("mcp_server_langgraph.hitl.broadcast.AgentRequestBroadcaster") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            result = registry.get_agent_request_broadcaster()

        assert result == mock_instance
        mock_class.assert_called_once()

    def test_get_agent_request_broadcaster_returns_singleton(self) -> None:
        """GIVEN broadcaster exists WHEN getting broadcaster THEN returns same instance."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry._agent_request_broadcaster = mock_instance

        result = registry.get_agent_request_broadcaster()

        assert result is mock_instance

    def test_set_agent_request_broadcaster_overrides_instance(self) -> None:
        """GIVEN broadcaster exists WHEN setting new broadcaster THEN overrides it."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry.set_agent_request_broadcaster(mock_instance)

        assert registry._agent_request_broadcaster is mock_instance

    def test_get_broadcaster_alias(self) -> None:
        """GIVEN get_broadcaster alias WHEN calling THEN returns same as get_agent_request_broadcaster."""
        from mcp_server_langgraph.websocket import registry

        mock_instance = MagicMock()
        registry._agent_request_broadcaster = mock_instance

        result = registry.get_broadcaster()

        assert result is mock_instance


@pytest.mark.xdist_group(name="websocket_registry")
class TestRegistryExports:
    """Tests for registry module exports."""

    def test_all_exports_are_available(self) -> None:
        """GIVEN registry module WHEN checking __all__ THEN all exports exist."""
        from mcp_server_langgraph.websocket import registry

        expected_exports = [
            "get_notification_broadcaster",
            "set_notification_broadcaster",
            "get_alert_broadcaster",
            "set_alert_broadcaster",
            "get_audit_event_broadcaster",
            "set_audit_event_broadcaster",
            "get_agent_request_broadcaster",
            "set_agent_request_broadcaster",
            "get_broadcaster",
            # New broadcasters for budget, trace, and MCP aggregated
            "get_budget_alert_broadcaster",
            "set_budget_alert_broadcaster",
            "get_trace_broadcaster",
            "set_trace_broadcaster",
            "get_mcp_aggregated_broadcaster",
            "set_mcp_aggregated_broadcaster",
            # DevTools broadcaster
            "get_devtools_broadcaster",
            "set_devtools_broadcaster",
        ]

        for export in expected_exports:
            assert hasattr(registry, export), f"Missing export: {export}"

    def test_all_matches_expected_exports(self) -> None:
        """GIVEN registry module WHEN checking __all__ THEN matches expected."""
        from mcp_server_langgraph.websocket import registry

        expected_exports = {
            "get_notification_broadcaster",
            "set_notification_broadcaster",
            "get_alert_broadcaster",
            "set_alert_broadcaster",
            "get_audit_event_broadcaster",
            "set_audit_event_broadcaster",
            "get_agent_request_broadcaster",
            "set_agent_request_broadcaster",
            "get_broadcaster",
            # New broadcasters for budget, trace, and MCP aggregated
            "get_budget_alert_broadcaster",
            "set_budget_alert_broadcaster",
            "get_trace_broadcaster",
            "set_trace_broadcaster",
            "get_mcp_aggregated_broadcaster",
            "set_mcp_aggregated_broadcaster",
            # DevTools broadcaster
            "get_devtools_broadcaster",
            "set_devtools_broadcaster",
            # Orchestrator status broadcaster
            "get_orchestrator_status_broadcaster",
            "set_orchestrator_status_broadcaster",
        }

        assert set(registry.__all__) == expected_exports
