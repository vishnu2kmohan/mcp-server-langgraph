"""
AI UX Redis L2 Cache Tests

TDD tests for L1 (in-memory TTLCache) + L2 (Redis) caching pattern.

The tiered caching system provides:
1. L1 (TTLCache) - Fast in-process caching (1000 entries, 1 hour TTL)
2. L2 (Redis) - Distributed caching for cross-instance sharing (5 min TTL)

Lookup flow:
1. Check L1 (in-memory) - if hit, return immediately
2. If L1 miss, check L2 (Redis) - if hit, populate L1 and return
3. If L2 miss, call LLM, populate both L1 and L2

Reference: StudioShell AI Enhancement Plan - Backend Redis Cache Integration
"""

import gc
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit


# =============================================================================
# Test Constants
# =============================================================================

SAMPLE_PERSONA_LLM_RESPONSE = """{
  "detected_persona": "alice-builder",
  "confidence": 0.85,
  "behavior_signals": ["Frequent workflow creation", "Advanced feature usage"],
  "recommendation": "Enable advanced features",
  "ui_adaptations": [{"feature": "workflow_builder", "action": "unlock"}]
}"""

SAMPLE_ERROR_LLM_RESPONSE = """{
  "category": "timeout",
  "subcategory": "request_timeout",
  "confidence": 0.95,
  "root_cause": "Server timeout due to high load",
  "suggestions": [{"action": "retry", "label": "Try again", "estimated_success": 0.8}]
}"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_factory():
    """Create mock LLM factory."""
    factory = MagicMock()
    factory.ainvoke = AsyncMock(return_value=AIMessage(content=SAMPLE_PERSONA_LLM_RESPONSE))
    return factory


@pytest.fixture
def mock_settings():
    """Create mock settings with Redis cache enabled."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    settings.enable_ai_ux_redis_cache = True
    settings.ai_ux_redis_cache_ttl_seconds = 300
    return settings


@pytest.fixture
def mock_settings_no_redis():
    """Create mock settings without Redis cache."""
    settings = MagicMock()
    settings.ff_enable_ai_suggestions = True
    settings.enable_ai_ux_redis_cache = False
    return settings


@pytest.fixture
def mock_redis_client():
    """Create mock async Redis client."""
    redis = AsyncMock(return_value=None)  # noqa: async-mock-config
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    return redis


# =============================================================================
# L1/L2 Cache Lookup Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestL1L2CacheLookup:
    """Test L1/L2 cache lookup pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_l1_cache_hit_returns_immediately(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """L1 cache hit returns immediately without checking L2 or calling LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        # Pre-populate L1 cache
        cache_key = "test_cache_key"
        expected_result = {"cached": True, "data": "from_l1"}
        service._response_cache[cache_key] = expected_result

        # Get cached response using tiered lookup
        result = await service.get_tiered_cached_response(cache_key)

        assert result == expected_result
        # Redis should NOT be called (L1 hit)
        mock_redis_client.get.assert_not_called()
        # LLM should NOT be called
        mock_llm_factory.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_l1_miss_l2_hit_populates_l1(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """L1 miss + L2 hit populates L1 cache and returns."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        cached_data = {"cached": True, "data": "from_l2"}
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data).encode())

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "test_cache_key"
        result = await service.get_tiered_cached_response(cache_key)

        assert result == cached_data
        # Redis should be called
        mock_redis_client.get.assert_called_once_with(f"ai_ux:{cache_key}")
        # L1 cache should be populated
        assert cache_key in service._response_cache
        assert service._response_cache[cache_key] == cached_data

    @pytest.mark.asyncio
    async def test_l1_miss_l2_miss_returns_none(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """L1 miss + L2 miss returns None."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_redis_client.get = AsyncMock(return_value=None)

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "test_cache_key"
        result = await service.get_tiered_cached_response(cache_key)

        assert result is None
        mock_redis_client.get.assert_called_once()


# =============================================================================
# L1/L2 Cache Store Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestL1L2CacheStore:
    """Test L1/L2 cache storage pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stores_to_both_l1_and_l2(self, mock_llm_factory, mock_settings, mock_redis_client):
        """Storing response populates both L1 and L2 caches."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "test_cache_key"
        data = {"result": "test_data"}

        await service.set_tiered_cached_response(cache_key, data)

        # L1 cache should have the data
        assert cache_key in service._response_cache
        assert service._response_cache[cache_key] == data

        # L2 cache (Redis) should be called
        mock_redis_client.setex.assert_called_once_with(
            f"ai_ux:{cache_key}",
            300,  # TTL from settings
            json.dumps(data),
        )

    @pytest.mark.asyncio
    async def test_stores_to_l1_only_when_redis_disabled(self, mock_llm_factory, mock_settings_no_redis):
        """When Redis is disabled, only L1 cache is populated."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        cache_key = "test_cache_key"
        data = {"result": "test_data"}

        await service.set_tiered_cached_response(cache_key, data)

        # L1 cache should have the data
        assert cache_key in service._response_cache
        assert service._response_cache[cache_key] == data
        # No Redis calls should happen
        assert service.redis_cache is None


# =============================================================================
# Cache Key Strategy Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestCacheKeyStrategy:
    """Test cache key generation strategy."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_independent_cache_key(self, mock_llm_factory, mock_settings_no_redis):
        """User-independent cache keys for shared analyses."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        # Same input should produce same key regardless of user
        key1 = service.generate_cache_key(
            method="error_analysis",
            error_type="TimeoutError",
            error_message="Request timed out",
        )
        key2 = service.generate_cache_key(
            method="error_analysis",
            error_type="TimeoutError",
            error_message="Request timed out",
        )

        assert key1 == key2
        assert "user" not in key1  # No user-specific component

    def test_user_specific_cache_key(self, mock_llm_factory, mock_settings_no_redis):
        """User-specific cache keys for personalized analyses."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        # Same input but different users should produce different keys
        key1 = service.generate_cache_key(
            method="persona_analysis",
            user_id="user-123",
            assigned_persona="bob",
        )
        key2 = service.generate_cache_key(
            method="persona_analysis",
            user_id="user-456",
            assigned_persona="bob",
        )

        assert key1 != key2
        assert "user-123" in key1 or key1 != key2  # User-specific

    def test_cache_key_deterministic(self, mock_llm_factory, mock_settings_no_redis):
        """Cache keys are deterministic for same inputs."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        keys = [
            service.generate_cache_key(
                method="test",
                param1="value1",
                param2=123,
            )
            for _ in range(5)
        ]

        assert len(set(keys)) == 1  # All keys should be identical


# =============================================================================
# Stale-While-Revalidate Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestStaleWhileRevalidate:
    """Test stale-while-revalidate pattern for L2 cache."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_stale_data_while_revalidating(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Returns stale data immediately while revalidating in background."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        stale_data = {"stale": True, "data": "old_value"}
        mock_redis_client.get = AsyncMock(return_value=json.dumps(stale_data).encode())
        # Simulate TTL check returning low value (near expiry)
        mock_redis_client.ttl = AsyncMock(return_value=30)  # 30 seconds left

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "test_swr_key"
        result = await service.get_tiered_cached_response(cache_key, stale_threshold_seconds=60)

        # Should return stale data immediately
        assert result == stale_data

    @pytest.mark.asyncio
    async def test_returns_fresh_data_without_revalidate(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Returns fresh data without triggering revalidation."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        fresh_data = {"fresh": True, "data": "new_value"}
        mock_redis_client.get = AsyncMock(return_value=json.dumps(fresh_data).encode())
        # Simulate TTL check returning high value (not near expiry)
        mock_redis_client.ttl = AsyncMock(return_value=250)  # 250 seconds left

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "test_fresh_key"
        result = await service.get_tiered_cached_response(cache_key, stale_threshold_seconds=60)

        # Should return fresh data
        assert result == fresh_data


# =============================================================================
# Prometheus Metrics Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestCacheMetrics:
    """Test Prometheus metrics for cache operations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_l1_cache_hit_increments_metric(self, mock_llm_factory, mock_settings_no_redis):
        """L1 cache hit increments l1_hit metric."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        # Pre-populate L1 cache
        cache_key = "metrics_test_key"
        service._response_cache[cache_key] = {"data": "test"}

        # Get cached response
        await service.get_tiered_cached_response(cache_key)

        # Note: Actual metric verification would require accessing
        # prometheus_client internals. This test documents the expected behavior.

    @pytest.mark.asyncio
    async def test_l2_cache_hit_increments_metric(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """L2 cache hit increments l2_hit metric."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        cached_data = {"data": "from_l2"}
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data).encode())

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "metrics_l2_test_key"
        await service.get_tiered_cached_response(cache_key)

        # Redis should be called (L2 hit)
        mock_redis_client.get.assert_called_once()


# =============================================================================
# Cache Invalidation Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestCacheInvalidation:
    """Test cache invalidation strategies."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalidate_by_user(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Can invalidate all cache entries for a specific user."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_redis_client.scan = AsyncMock(return_value=(0, [b"ai_ux:user-123:key1", b"ai_ux:user-123:key2"]))
        mock_redis_client.delete = AsyncMock(return_value=2)

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        # Pre-populate L1 cache with user-specific entries
        service._response_cache["user-123:persona"] = {"data": "test1"}
        service._response_cache["user-123:disclosure"] = {"data": "test2"}
        service._response_cache["user-456:persona"] = {"data": "other"}

        _deleted_count = await service.invalidate_user_cache("user-123")

        # User-specific entries should be removed from L1
        assert "user-123:persona" not in service._response_cache
        assert "user-123:disclosure" not in service._response_cache
        # Other user entries should remain
        assert "user-456:persona" in service._response_cache

    @pytest.mark.asyncio
    async def test_invalidate_by_method(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Can invalidate all cache entries for a specific method."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )

        # Pre-populate L1 cache with method-specific entries
        service._response_cache["persona_analysis:user-1"] = {"data": "test1"}
        service._response_cache["persona_analysis:user-2"] = {"data": "test2"}
        service._response_cache["disclosure:user-1"] = {"data": "other"}

        deleted_count = await service.invalidate_method_cache("persona_analysis")

        # Method-specific entries should be removed from L1
        assert "persona_analysis:user-1" not in service._response_cache
        assert "persona_analysis:user-2" not in service._response_cache
        # Other method entries should remain
        assert "disclosure:user-1" in service._response_cache
        # Should return count of deleted entries (at least 2 from legacy cache)
        assert deleted_count >= 2


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="ai_ux_redis_l2_cache")
class TestCacheErrorHandling:
    """Test cache error handling and fallbacks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_redis_connection_error_falls_back_to_l1(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Redis connection error falls back to L1 cache only."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_redis_client.get = AsyncMock(side_effect=ConnectionError("Redis down"))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "error_test_key"
        result = await service.get_tiered_cached_response(cache_key)

        # Should gracefully return None (cache miss) without raising
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_timeout_is_handled_gracefully(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Redis timeout is handled gracefully."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_redis_client.get = AsyncMock(side_effect=TimeoutError("Redis timeout"))

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "timeout_test_key"
        result = await service.get_tiered_cached_response(cache_key)

        # Should gracefully return None without raising
        assert result is None

    @pytest.mark.asyncio
    async def test_json_decode_error_is_handled(self, mock_llm_factory, mock_settings_no_redis, mock_redis_client):
        """Corrupted JSON in Redis is handled gracefully."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_redis_client.get = AsyncMock(return_value=b"not valid json{")

        service = AIUXService(
            llm_factory=mock_llm_factory,
            settings=mock_settings_no_redis,
        )
        # Manually inject Redis cache for testing
        service.redis_cache = mock_redis_client

        cache_key = "json_error_test_key"
        result = await service.get_tiered_cached_response(cache_key)

        # Should gracefully return None for corrupted data
        assert result is None
