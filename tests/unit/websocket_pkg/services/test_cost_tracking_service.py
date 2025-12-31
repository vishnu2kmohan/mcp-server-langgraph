"""
Tests for Cost Tracking Service Adapter.

TDD tests for CostTrackingServiceAdapter - verifies session cost retrieval
and user budget functionality.

PYTEST-XDIST FIX: Uses gc.collect() in teardown for memory safety.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.websocket.services.cost_tracking import (
    CostTrackingServiceAdapter,
    reset_websocket_cost_service,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="cost_tracking_service")
class TestCostTrackingServiceAdapter:
    """Tests for CostTrackingServiceAdapter session cost retrieval."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_cost_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_cost_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_cost_returns_cached_data(self) -> None:
        """get_session_cost returns data from Redis cache when available."""
        mock_cache = AsyncMock()  # noqa: async-mock-config
        mock_cache.aget.return_value = {
            "session_id": "session-123",
            "total_cost": 0.05,
            "token_count": 1500,
            "updated_at": "2025-12-31T00:00:00Z",
        }

        adapter = CostTrackingServiceAdapter(cache=mock_cache)
        result = await adapter.get_session_cost("session-123")

        assert result["session_id"] == "session-123"
        assert result["total_cost"] == 0.05
        assert result["token_count"] == 1500
        mock_cache.aget.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_cost_falls_back_to_memory_on_redis_error(self) -> None:
        """get_session_cost falls back to in-memory cache on Redis error."""
        mock_cache = AsyncMock()  # noqa: async-mock-config
        mock_cache.aget.side_effect = Exception("Redis connection failed")

        adapter = CostTrackingServiceAdapter(cache=mock_cache)
        # Pre-populate in-memory cache
        adapter._session_costs["session-456"] = {
            "session_id": "session-456",
            "total_cost": 0.10,
            "token_count": 3000,
        }

        result = await adapter.get_session_cost("session-456")

        assert result["session_id"] == "session-456"
        assert result["total_cost"] == 0.10

    @pytest.mark.asyncio
    async def test_get_session_cost_returns_zeros_when_no_data(self) -> None:
        """get_session_cost returns zero cost when no cached data exists."""
        mock_cache = AsyncMock()  # noqa: async-mock-config
        mock_cache.aget.return_value = None

        adapter = CostTrackingServiceAdapter(cache=mock_cache)

        with patch("mcp_server_langgraph.websocket.services.cost_tracking.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_websocket_enhanced_metrics=True)
            result = await adapter.get_session_cost("new-session")

        assert result["session_id"] == "new-session"
        assert result["total_cost"] == 0.0
        assert result["token_count"] == 0

    @pytest.mark.asyncio
    async def test_update_session_cost_async_updates_cache(self) -> None:
        """update_session_cost_async updates both Redis and in-memory cache."""
        mock_cache = AsyncMock()  # noqa: async-mock-config
        mock_cache.aget.return_value = None

        adapter = CostTrackingServiceAdapter(cache=mock_cache)
        result = await adapter.update_session_cost_async("session-789", 0.02, 500)

        assert result["session_id"] == "session-789"
        assert result["total_cost"] == 0.02
        assert result["token_count"] == 500
        mock_cache.aset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_cost_async_accumulates_costs(self) -> None:
        """update_session_cost_async adds to existing costs."""
        mock_cache = AsyncMock()  # noqa: async-mock-config
        mock_cache.aget.return_value = {
            "session_id": "session-acc",
            "total_cost": 0.05,
            "token_count": 1000,
        }

        adapter = CostTrackingServiceAdapter(cache=mock_cache)
        result = await adapter.update_session_cost_async("session-acc", 0.03, 600)

        assert result["total_cost"] == 0.08  # 0.05 + 0.03
        assert result["token_count"] == 1600  # 1000 + 600


@pytest.mark.unit
@pytest.mark.xdist_group(name="cost_tracking_service")
class TestCostTrackingUserBudget:
    """Tests for CostTrackingServiceAdapter user budget functionality."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_websocket_cost_service()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        reset_websocket_cost_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_user_budget_returns_cached_budget(self) -> None:
        """get_user_budget returns cached budget data when available."""
        adapter = CostTrackingServiceAdapter()
        # Pre-populate budget cache
        adapter._user_budgets["user:alice"] = {
            "user_id": "user:alice",
            "budget_limit": 50.0,
            "current_usage": 15.0,
            "remaining": 35.0,
        }

        result = await adapter.get_user_budget("user:alice")

        assert result["user_id"] == "user:alice"
        assert result["budget_limit"] == 50.0
        assert result["current_usage"] == 15.0
        assert result["remaining"] == 35.0

    @pytest.mark.asyncio
    async def test_get_user_budget_returns_default_when_not_found(self) -> None:
        """get_user_budget returns default budget when user not found."""
        adapter = CostTrackingServiceAdapter()

        result = await adapter.get_user_budget("user:newuser")

        assert result["user_id"] == "user:newuser"
        assert result["budget_limit"] == 100.0  # Default
        assert result["current_usage"] == 0.0
        assert result["remaining"] == 100.0

    @pytest.mark.asyncio
    async def test_invalidate_session_cost_clears_cache(self) -> None:
        """invalidate_session_cost removes session from both caches."""
        mock_cache = AsyncMock()  # noqa: async-mock-config

        adapter = CostTrackingServiceAdapter(cache=mock_cache)
        adapter._session_costs["session-delete"] = {
            "session_id": "session-delete",
            "total_cost": 1.0,
            "token_count": 10000,
        }

        await adapter.invalidate_session_cost("session-delete")

        assert "session-delete" not in adapter._session_costs
        mock_cache.adelete.assert_called_once()
