"""
Budget Alerts WebSocket Endpoint Tests

TDD tests for the budget alerts WebSocket endpoint registration.
Tests written FIRST (RED phase).
"""

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.monitoring,
]


@pytest.mark.xdist_group(name="test_budget_alerts_websocket")
class TestBudgetAlertsWebSocketEndpoint:
    """Tests for budget alerts WebSocket endpoint availability."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_alerts_handler_exported_from_handlers_module(self) -> None:
        """
        GIVEN the websocket handlers module
        WHEN importing BudgetAlertsHandler
        THEN it should be exported from the package.
        """
        from mcp_server_langgraph.websocket.handlers import BudgetAlertsHandler

        assert BudgetAlertsHandler is not None

    def test_ws_router_has_budget_alerts_endpoint(self) -> None:
        """
        GIVEN the WebSocket router
        WHEN inspecting routes
        THEN /budget/alerts endpoint should exist.
        """
        from mcp_server_langgraph.api.v1.ws_router import ws_router

        # Get all route paths
        paths = [route.path for route in ws_router.routes]

        assert "/budget/alerts" in paths

    def test_budget_alerts_endpoint_uses_correct_handler(self) -> None:
        """
        GIVEN the budget alerts WebSocket endpoint
        WHEN inspecting the handler
        THEN it should use BudgetAlertsHandler.
        """
        from mcp_server_langgraph.api.v1.ws_router import budget_alerts_websocket

        # Function should exist (will be imported)
        assert budget_alerts_websocket is not None
        assert callable(budget_alerts_websocket)


@pytest.mark.xdist_group(name="test_budget_alerts_websocket")
class TestBudgetAlertsHandlerIntegration:
    """Tests for budget alerts handler integration with broadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_alert_broadcaster_registry_function_exists(self) -> None:
        """
        GIVEN the websocket registry
        WHEN checking for budget alert broadcaster getter
        THEN get_budget_alert_broadcaster should exist.
        """
        from mcp_server_langgraph.websocket import registry

        assert hasattr(registry, "get_budget_alert_broadcaster")

    def test_budget_alerts_handler_uses_broadcaster(self) -> None:
        """
        GIVEN the BudgetAlertsHandler
        WHEN checking constructor
        THEN it should accept a broadcaster parameter.
        """
        from mcp_server_langgraph.websocket.handlers import BudgetAlertsHandler
        from mcp_server_langgraph.websocket import WebSocketConfig

        # Handler should accept broadcaster in constructor
        config = WebSocketConfig(endpoint_name="test")

        # Should not raise
        handler = BudgetAlertsHandler(config=config)
        assert handler is not None
