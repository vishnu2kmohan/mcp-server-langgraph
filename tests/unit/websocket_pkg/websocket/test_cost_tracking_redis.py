"""
Tests for Redis Session Cost Caching.

TDD: Tests written FIRST before implementation.

This module tests the Redis integration for session cost caching in the
CostTrackingServiceAdapter. The Redis cache allows real-time cost tracking
to be shared across WebSocket connections and server instances.

Key patterns:
- Key format: session_cost:{session_id}
- TTL: 1 hour for active sessions
- Data: {session_id, total_cost, token_count, updated_at}
"""

import gc
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Memory safety for pytest-xdist
pytestmark = [
    pytest.mark.xdist_group(name="websocket_cost_tracking"),
    pytest.mark.unit,
]


@pytest.fixture
def mock_cache_service():
    """Create a mock CacheService for testing."""
    cache = MagicMock()
    cache.aget = AsyncMock(return_value=None)
    cache.aset = AsyncMock(return_value=None)  # Explicit config per guidelines
    cache.adelete = AsyncMock(return_value=None)  # Explicit config per guidelines
    cache.redis_available = True
    return cache


class TestCostTrackingServiceAdapterRedis:
    """Tests for Redis-backed session cost caching."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_session_cost_from_redis_cache(self, mock_cache_service):
        """
        GIVEN a session ID with cost data cached in Redis
        WHEN get_session_cost is called
        THEN it should return the cached cost data without querying the database
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # Set up cached data
        cached_data = {
            "session_id": "session-123",
            "total_cost": 0.0123,
            "token_count": 1500,
            "updated_at": datetime.now().isoformat(),
        }
        mock_cache_service.aget.return_value = cached_data

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Call get_session_cost
        result = await adapter.get_session_cost("session-123")

        # Verify cache was checked with correct key
        mock_cache_service.aget.assert_called_once_with("session_cost:session-123")

        # Verify result matches cached data
        assert result["session_id"] == "session-123"
        assert result["total_cost"] == 0.0123
        assert result["token_count"] == 1500

    @pytest.mark.asyncio
    async def test_get_session_cost_cache_miss_returns_initial_values(self, mock_cache_service):
        """
        GIVEN a session ID with no cached data
        WHEN get_session_cost is called
        THEN it should return initial values (0.0 cost, 0 tokens)

        Note: The cache is populated by LLM calls via update_session_cost_async.
        If there's no cache entry, it means no LLM calls have been made for the
        session yet, so 0.0 cost is the correct initial value.
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # Cache miss
        mock_cache_service.aget.return_value = None

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Call get_session_cost
        result = await adapter.get_session_cost("session-456")

        # Verify cache was checked
        mock_cache_service.aget.assert_called_once_with("session_cost:session-456")

        # Verify result has initial values
        assert result["session_id"] == "session-456"
        assert result["total_cost"] == 0.0
        assert result["token_count"] == 0

    @pytest.mark.asyncio
    async def test_update_session_cost_updates_redis_cache(self, mock_cache_service):
        """
        GIVEN an adapter with Redis cache
        WHEN update_session_cost is called with new cost data
        THEN the Redis cache should be updated with accumulated values
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # Existing cached data
        existing_data = {
            "session_id": "session-789",
            "total_cost": 0.01,
            "token_count": 1000,
            "updated_at": datetime.now().isoformat(),
        }
        mock_cache_service.aget.return_value = existing_data

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Update with new cost
        result = await adapter.update_session_cost_async(session_id="session-789", cost=0.005, tokens=500)

        # Verify cache was updated with accumulated values
        mock_cache_service.aset.assert_called_once()
        call_args = mock_cache_service.aset.call_args
        cached_value = call_args[0][1]
        assert cached_value["total_cost"] == 0.015  # 0.01 + 0.005
        assert cached_value["token_count"] == 1500  # 1000 + 500
        assert cached_value["session_id"] == "session-789"

        # Verify result
        assert result["total_cost"] == 0.015
        assert result["token_count"] == 1500

    @pytest.mark.asyncio
    async def test_update_session_cost_creates_new_cache_entry(self, mock_cache_service):
        """
        GIVEN a session with no existing cache entry
        WHEN update_session_cost is called
        THEN a new cache entry should be created
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # No existing cache
        mock_cache_service.aget.return_value = None

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Update with new cost
        result = await adapter.update_session_cost_async(session_id="new-session", cost=0.002, tokens=250)

        # Verify cache was created
        mock_cache_service.aset.assert_called_once()
        call_args = mock_cache_service.aset.call_args
        cached_value = call_args[0][1]
        assert cached_value["total_cost"] == 0.002
        assert cached_value["token_count"] == 250
        assert cached_value["session_id"] == "new-session"
        assert call_args[1]["ttl"] == 3600

        # Verify result
        assert result["total_cost"] == 0.002
        assert result["token_count"] == 250

    @pytest.mark.asyncio
    async def test_get_session_cost_graceful_degradation_when_redis_unavailable(self, mock_cache_service):
        """
        GIVEN Redis is unavailable (cache.aget raises exception)
        WHEN get_session_cost is called
        THEN it should fall back to in-memory cache without crashing
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # Redis error
        mock_cache_service.aget.side_effect = Exception("Redis connection failed")
        mock_cache_service.redis_available = False

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Pre-populate in-memory cache
        adapter._session_costs["session-fallback"] = {
            "session_id": "session-fallback",
            "total_cost": 0.05,
            "token_count": 2000,
        }

        # Should not raise, should fall back to in-memory
        result = await adapter.get_session_cost("session-fallback")

        assert result["session_id"] == "session-fallback"
        assert result["total_cost"] == 0.05
        assert result["token_count"] == 2000

    @pytest.mark.asyncio
    async def test_cache_key_format(self, mock_cache_service):
        """
        GIVEN a session ID
        WHEN interacting with Redis cache
        THEN the key format should be 'session_cost:{session_id}'
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        mock_cache_service.aget.return_value = None

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        await adapter.get_session_cost("my-special-session-123")

        # Verify the exact key format
        mock_cache_service.aget.assert_called_with("session_cost:my-special-session-123")

    @pytest.mark.asyncio
    async def test_cache_ttl_is_one_hour(self, mock_cache_service):
        """
        GIVEN cost data being cached via update
        WHEN aset is called
        THEN TTL should be 3600 seconds (1 hour)
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            SESSION_COST_CACHE_TTL,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        mock_cache_service.aget.return_value = None

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Use update_session_cost_async which caches with TTL
        await adapter.update_session_cost_async("session-ttl-test", 0.01, 100)

        # Verify TTL was used
        call_args = mock_cache_service.aset.call_args
        assert call_args[1]["ttl"] == 3600
        assert SESSION_COST_CACHE_TTL == 3600

    @pytest.mark.asyncio
    async def test_invalidate_session_cost_cache(self, mock_cache_service):
        """
        GIVEN a session with cached cost data
        WHEN invalidate_session_cost is called
        THEN the cache entry should be deleted
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            CostTrackingServiceAdapter,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        adapter = CostTrackingServiceAdapter()
        adapter._cache = mock_cache_service

        # Invalidate cache
        await adapter.invalidate_session_cost("session-to-clear")

        # Verify cache was deleted
        mock_cache_service.adelete.assert_called_once_with("session_cost:session-to-clear")

        # Also verify in-memory cache was cleared
        adapter._session_costs["session-to-clear"] = {"some": "data"}
        await adapter.invalidate_session_cost("session-to-clear")
        assert "session-to-clear" not in adapter._session_costs


class TestCostMetricsCollectorRedisIntegration:
    """Tests for wiring CostMetricsCollector.record_usage to update Redis cache."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_usage_updates_session_cost_cache(self):
        """
        GIVEN cost recording via CostMetricsCollector
        WHEN record_usage is called with session_id
        THEN the Redis session cost cache should be updated
        """
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            get_websocket_cost_service,
            reset_websocket_cost_service,
        )

        reset_websocket_cost_service()

        # Mock the update function
        with patch.object(
            get_websocket_cost_service(),
            "update_session_cost_async",
            new_callable=AsyncMock,
        ) as mock_update:
            # Import after patching to get the patched version
            from mcp_server_langgraph.monitoring.cost_tracker import (
                update_session_cost_cache,
            )

            # Call the integration function
            await update_session_cost_cache(
                session_id="session-record-test",
                cost=0.0089,
                tokens=750,
            )

            # Verify update was called
            mock_update.assert_called_once_with(
                session_id="session-record-test",
                cost=0.0089,
                tokens=750,
            )


class TestSessionCostCacheKeyConstants:
    """Tests for cache key constants and configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_cost_cache_key_prefix(self):
        """Verify the cache key prefix constant exists."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            SESSION_COST_CACHE_KEY_PREFIX,
        )

        assert SESSION_COST_CACHE_KEY_PREFIX == "session_cost"

    def test_session_cost_cache_ttl(self):
        """Verify the cache TTL constant exists and is 1 hour."""
        from mcp_server_langgraph.websocket.services.cost_tracking import (
            SESSION_COST_CACHE_TTL,
        )

        assert SESSION_COST_CACHE_TTL == 3600  # 1 hour in seconds
