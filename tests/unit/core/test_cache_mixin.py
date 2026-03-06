"""
TieredCacheMixin Unit Tests

TDD tests for the cache mixin that provides DRY caching capabilities.
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


class TestTieredCacheMixin:
    """Tests for TieredCacheMixin functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mixin_provides_cache_prefix(self) -> None:
        """Mixin classes should define cache_prefix for namespacing."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test_service"

        service = TestService()
        assert service.cache_prefix == "test_service"

    def test_mixin_provides_cache_ttl(self) -> None:
        """Mixin classes should define cache_ttl for expiration."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"
            cache_ttl = 600

        service = TestService()
        assert service.cache_ttl == 600

    def test_make_cache_key_with_single_part(self) -> None:
        """_make_cache_key should generate prefixed key from single part."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "my_service"

        service = TestService()
        key = service._make_cache_key("user123")
        assert key == "my_service:user123"

    def test_make_cache_key_with_multiple_parts(self) -> None:
        """_make_cache_key should join multiple parts with colon."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "ai_ux"

        service = TestService()
        key = service._make_cache_key("persona", "user123", "v2")
        assert key == "ai_ux:persona:user123:v2"

    @pytest.mark.asyncio
    async def test_cache_get_returns_cached_value(self) -> None:
        """_cache_get should return value from cache when present."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        # Mock the cache service
        mock_cache = MagicMock()
        mock_cache.aget = AsyncMock(return_value={"data": "cached"})
        service._cache_service = mock_cache

        result = await service._cache_get("test:key")
        assert result == {"data": "cached"}
        mock_cache.aget.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_on_miss(self) -> None:
        """_cache_get should return None when key not in cache."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.aget = AsyncMock(return_value=None)
        service._cache_service = mock_cache

        result = await service._cache_get("test:missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_stores_value_with_ttl(self) -> None:
        """_cache_set should store value with specified TTL."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"
            cache_ttl = 300

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.aset = AsyncMock(return_value=None)
        service._cache_service = mock_cache

        await service._cache_set("test:key", {"value": 123})
        mock_cache.aset.assert_called_once_with("test:key", {"value": 123}, ttl=300)

    @pytest.mark.asyncio
    async def test_cache_set_with_custom_ttl(self) -> None:
        """_cache_set should allow overriding TTL."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"
            cache_ttl = 300

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.aset = AsyncMock(return_value=None)
        service._cache_service = mock_cache

        await service._cache_set("test:key", {"value": 123}, ttl=600)
        mock_cache.aset.assert_called_once_with("test:key", {"value": 123}, ttl=600)

    @pytest.mark.asyncio
    async def test_cache_delete_removes_key(self) -> None:
        """_cache_delete should remove key from cache."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.adelete = AsyncMock(return_value=None)
        service._cache_service = mock_cache

        await service._cache_delete("test:key")
        mock_cache.adelete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_invalidate_prefix_deletes_pattern(self) -> None:
        """_cache_invalidate_prefix should delete all keys matching pattern."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "ai_ux"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=5)
        service._cache_service = mock_cache

        count = await service._cache_invalidate_prefix("persona")
        assert count == 5
        mock_cache.adelete_pattern.assert_called_once_with("ai_ux:persona:*")

    @pytest.mark.asyncio
    async def test_cache_invalidate_user_clears_user_keys(self) -> None:
        """_cache_invalidate_user should clear all keys for a user."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "my_service"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=3)
        service._cache_service = mock_cache

        count = await service._cache_invalidate_user("user123")
        assert count == 3
        mock_cache.adelete_pattern.assert_called_once_with("my_service:*:user123:*")

    def test_cache_property_lazy_initializes(self) -> None:
        """_cache property should lazy-initialize CacheService."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        # Should not have _cache_service yet
        assert not hasattr(service, "_cache_service") or service._cache_service is None

        # Mock get_cache to avoid real initialization
        with patch("mcp_server_langgraph.core.cache_mixin.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            # Access _cache property
            cache = service._cache
            assert cache == mock_cache
            mock_get_cache.assert_called_once()

    def test_generate_user_cache_key(self) -> None:
        """_make_user_cache_key should include user_id in key."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "ai_ux"

        service = TestService()
        key = service._make_user_cache_key("persona", "user123")
        assert key == "ai_ux:persona:user123"

    def test_generate_method_cache_key_with_hash(self) -> None:
        """_make_method_cache_key should hash request data."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "ai_ux"

        service = TestService()
        key = service._make_method_cache_key("analyze", {"user_id": "123", "data": "test"})

        # Should start with prefix:method:
        assert key.startswith("ai_ux:analyze:")
        # Should have hash suffix
        assert len(key) > len("ai_ux:analyze:")

    def test_method_cache_key_deterministic(self) -> None:
        """Same request data should generate same cache key."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()
        request = {"user_id": "123", "action": "analyze"}

        key1 = service._make_method_cache_key("method", request)
        key2 = service._make_method_cache_key("method", request)
        assert key1 == key2

    def test_method_cache_key_different_for_different_data(self) -> None:
        """Different request data should generate different cache keys."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        key1 = service._make_method_cache_key("method", {"user": "a"})
        key2 = service._make_method_cache_key("method", {"user": "b"})
        assert key1 != key2


class TestTieredCacheMixinMetrics:
    """Tests for cache mixin metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_hit_increments_metric(self) -> None:
        """Cache hit should increment hit metric."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.aget = AsyncMock(return_value={"data": "cached"})
        service._cache_service = mock_cache

        with patch("mcp_server_langgraph.core.cache_mixin.CACHE_MIXIN_HITS") as mock_hits:
            mock_counter = MagicMock()
            mock_hits.labels.return_value = mock_counter

            await service._cache_get_with_metrics("test:key", method="analyze")

            mock_hits.labels.assert_called_with(service="test", method="analyze")
            mock_counter.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_increments_metric(self) -> None:
        """Cache miss should increment miss metric."""
        from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

        class TestService(TieredCacheMixin):
            cache_prefix = "test"

        service = TestService()

        mock_cache = MagicMock()
        mock_cache.aget = AsyncMock(return_value=None)
        service._cache_service = mock_cache

        with patch("mcp_server_langgraph.core.cache_mixin.CACHE_MIXIN_MISSES") as mock_misses:
            mock_counter = MagicMock()
            mock_misses.labels.return_value = mock_counter

            await service._cache_get_with_metrics("test:key", method="analyze")

            mock_misses.labels.assert_called_with(service="test", method="analyze")
            mock_counter.inc.assert_called_once()
