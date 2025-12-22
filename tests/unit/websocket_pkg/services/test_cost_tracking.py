"""Unit tests for WebSocket CostTrackingServiceAdapter.

Tests the CostTrackingServiceAdapter that provides session-level cost tracking
for WebSocket handlers.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_cost_tracking")
class TestCostTrackingServiceAdapter:
    """Test suite for CostTrackingServiceAdapter."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            reset_websocket_cost_service,
        )
        reset_websocket_cost_service()
        gc.collect()

    def test_init_without_cost_service(self) -> None:
        """Test adapter initialization without cost service."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        assert adapter._cost_service is None
        assert adapter._session_costs == {}
        assert adapter._user_budgets == {}

    def test_init_with_cost_service(self) -> None:
        """Test adapter initialization with cost service."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        mock_service = MagicMock()
        adapter = CostTrackingServiceAdapter(cost_service=mock_service)

        assert adapter._cost_service is mock_service

    def test_cost_service_property_lazy_init(self) -> None:
        """Test cost_service property lazily initializes the service."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        # Patch at the source location where get_cost_service is defined
        with patch(
            "mcp_server_langgraph.api.v1.cost.get_cost_service"
        ) as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service

            result = adapter.cost_service

            assert result is mock_service
            mock_get.assert_called_once()

    def test_cost_service_property_returns_cached(self) -> None:
        """Test cost_service property returns cached instance."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        mock_service = MagicMock()
        adapter = CostTrackingServiceAdapter(cost_service=mock_service)

        # Access multiple times
        result1 = adapter.cost_service
        result2 = adapter.cost_service

        assert result1 is result2 is mock_service

    @pytest.mark.asyncio
    async def test_get_session_cost_returns_cached_data(self) -> None:
        """Test get_session_cost returns cached session cost."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()
        adapter._session_costs["session-1"] = {
            "session_id": "session-1",
            "total_cost": 5.25,
            "token_count": 1500,
        }

        result = await adapter.get_session_cost("session-1")

        assert result["session_id"] == "session-1"
        assert result["total_cost"] == 5.25
        assert result["token_count"] == 1500

    @pytest.mark.asyncio
    async def test_get_session_cost_returns_stub_when_not_cached(self) -> None:
        """Test get_session_cost returns stub data for unknown session."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        with patch(
            "mcp_server_langgraph.websocket.services.cost_tracking.get_feature_flags"
        ) as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = True
            mock_flags.return_value = mock_ff

            result = await adapter.get_session_cost("unknown-session")

            assert result["session_id"] == "unknown-session"
            assert result["total_cost"] == 0.0
            assert result["token_count"] == 0

    @pytest.mark.asyncio
    async def test_get_session_cost_minimal_when_metrics_disabled(self) -> None:
        """Test get_session_cost returns minimal stub when metrics disabled."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        with patch(
            "mcp_server_langgraph.websocket.services.cost_tracking.get_feature_flags"
        ) as mock_flags:
            mock_ff = MagicMock()
            mock_ff.enable_websocket_enhanced_metrics = False
            mock_flags.return_value = mock_ff

            result = await adapter.get_session_cost("session-x")

            assert result["session_id"] == "session-x"
            assert result["total_cost"] == 0.0
            assert result["token_count"] == 0

    @pytest.mark.asyncio
    async def test_get_user_budget_returns_cached_data(self) -> None:
        """Test get_user_budget returns cached budget data."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()
        adapter._user_budgets["user-1"] = {
            "user_id": "user-1",
            "budget_limit": 50.0,
            "current_usage": 25.0,
            "remaining": 25.0,
        }

        result = await adapter.get_user_budget("user-1")

        assert result["user_id"] == "user-1"
        assert result["budget_limit"] == 50.0
        assert result["current_usage"] == 25.0
        assert result["remaining"] == 25.0

    @pytest.mark.asyncio
    async def test_get_user_budget_returns_stub_when_not_cached(self) -> None:
        """Test get_user_budget returns stub data for unknown user."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        result = await adapter.get_user_budget("unknown-user")

        assert result["user_id"] == "unknown-user"
        assert result["budget_limit"] == 100.0  # Default $100 budget
        assert result["current_usage"] == 0.0
        assert result["remaining"] == 100.0

    def test_update_session_cost_creates_new_entry(self) -> None:
        """Test update_session_cost creates new session cost entry."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        result = adapter.update_session_cost("session-new", cost=2.50, tokens=500)

        assert result["session_id"] == "session-new"
        assert result["total_cost"] == 2.50
        assert result["token_count"] == 500

    def test_update_session_cost_adds_to_existing(self) -> None:
        """Test update_session_cost adds to existing session cost."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()
        adapter._session_costs["session-1"] = {
            "session_id": "session-1",
            "total_cost": 5.0,
            "token_count": 1000,
        }

        result = adapter.update_session_cost("session-1", cost=2.50, tokens=500)

        assert result["total_cost"] == 7.50
        assert result["token_count"] == 1500

    def test_update_session_cost_multiple_updates(self) -> None:
        """Test update_session_cost accumulates multiple updates."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
        )

        adapter = CostTrackingServiceAdapter()

        adapter.update_session_cost("session-1", cost=1.0, tokens=100)
        adapter.update_session_cost("session-1", cost=2.0, tokens=200)
        result = adapter.update_session_cost("session-1", cost=3.0, tokens=300)

        assert result["total_cost"] == 6.0
        assert result["token_count"] == 600


@pytest.mark.unit
@pytest.mark.xdist_group(name="websocket_services_cost_tracking")
class TestCostTrackingSingleton:
    """Test suite for cost tracking service singleton functions."""

    def teardown_method(self) -> None:
        """Force GC and reset singleton to prevent mock accumulation."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            reset_websocket_cost_service,
        )
        reset_websocket_cost_service()
        gc.collect()

    def test_get_websocket_cost_service_creates_singleton(self) -> None:
        """Test get_websocket_cost_service creates singleton instance."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            get_websocket_cost_service,
            CostTrackingServiceAdapter,
        )

        result = get_websocket_cost_service()

        assert isinstance(result, CostTrackingServiceAdapter)

    def test_get_websocket_cost_service_returns_same_instance(self) -> None:
        """Test get_websocket_cost_service returns same instance on multiple calls."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            get_websocket_cost_service,
        )

        result1 = get_websocket_cost_service()
        result2 = get_websocket_cost_service()

        assert result1 is result2

    def test_reset_websocket_cost_service_clears_singleton(self) -> None:
        """Test reset_websocket_cost_service clears singleton."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            get_websocket_cost_service,
            reset_websocket_cost_service,
        )

        first = get_websocket_cost_service()
        reset_websocket_cost_service()
        second = get_websocket_cost_service()

        assert first is not second
