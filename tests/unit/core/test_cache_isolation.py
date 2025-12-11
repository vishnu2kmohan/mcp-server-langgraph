"""
🔴 RED → 🟢 GREEN PHASE - Tests for cache database isolation

SECURITY FINDING #6: Cache invalidation scope issue.

Both L2 cache and API key cache use Redis DB 2. When cache.clear() is called
without a pattern, it uses flushdb() which clears the ENTIRE database,
affecting BOTH caches (unintended data loss).

Expected to FAIL until:
1. API key cache moved to separate Redis DB (config.py api_key_cache_db: 2 → 3)
2. flushdb() replaced with pattern-based deletion (cache.py)
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def test_api_key_cache_uses_separate_database(monkeypatch):
    """
    🟢 GREEN: Test that API key cache uses different Redis DB than L2 cache.

    PROBLEM: Both use DB 2, causing cache.clear() to affect API keys.

    This test should PASS after changing api_key_cache_db to 3.

    **pytest-xdist Isolation:**
    - Uses monkeypatch.setenv() for automatic environment cleanup

    References:
    - tests/regression/test_pytest_xdist_environment_pollution.py
    - OpenAI Codex Finding: test_cache_isolation.py:27
    """
    # Use monkeypatch for automatic cleanup (prevents environment pollution)
    monkeypatch.setenv("ENVIRONMENT", "test")

    from mcp_server_langgraph.core.config import Settings

    settings = Settings()

    # L2 cache uses DB 2 (default redis_cache_db in CacheService)
    l2_cache_db = getattr(settings, "redis_cache_db", 2)

    # API key cache DB
    api_key_cache_db = settings.api_key_cache_db

    assert api_key_cache_db != l2_cache_db, (
        f"API key cache must use different Redis DB than L2 cache. "
        f"L2 cache DB: {l2_cache_db}, API key cache DB: {api_key_cache_db}. "
        "If they share the same DB, cache.clear() will flush BOTH caches!"
    )


@pytest.mark.xdist_group(name="cache_isolation")
class TestCacheIsolation:
    """
    Tests for cache isolation and pattern-based deletion.

    Uses xdist_group for proper worker isolation and teardown_method
    with gc.collect() to prevent memory leaks in pytest-xdist.

    References:
    - tests/MEMORY_SAFETY_GUIDELINES.md
    - ADR-0052: Pytest-xdist Isolation Strategy
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cache_clear_without_pattern_does_not_use_flushdb(self):
        """
        🟢 GREEN: Test that cache.clear() without pattern uses pattern-based deletion, not flushdb().

        PROBLEM: cache.clear() without pattern calls flushdb() which clears entire Redis DB.
        This affects all data in that DB, including API key cache if sharing DB 2.

        This test should PASS after replacing flushdb() with pattern-based deletion.

        XDIST FIX: Import CacheService before patching and directly inject mock attributes.
        This avoids import-time module caching issues under pytest-xdist.
        """
        from mcp_server_langgraph.core.cache import CacheService

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"cache:key1", b"cache:key2", b"cache:key3"]

        # Mock L1 cache (TTLCache-like)
        mock_l1_cache = MagicMock()

        # Create CacheService with mock injection (bypass __init__)
        with patch.object(CacheService, "__init__", lambda self, **kwargs: None):
            cache = CacheService.__new__(CacheService)
            # Inject required attributes that clear() uses
            cache.redis = mock_redis
            cache.redis_available = True
            cache.l1_cache = mock_l1_cache

            # Clear all cache without pattern
            cache.clear()

            # Should NOT call flushdb
            assert not mock_redis.flushdb.called, (
                "cache.clear() should NOT use flushdb() - it clears entire Redis DB! "
                "Use pattern-based deletion (keys('*') + delete) instead."
            )

            # Should clear L1 cache
            mock_l1_cache.clear.assert_called_once()

            # Should use pattern-based deletion for L2 (Redis)
            mock_redis.keys.assert_called_with("*")  # Should scan for all keys
            mock_redis.delete.assert_called_once_with(b"cache:key1", b"cache:key2", b"cache:key3")

    def test_cache_service_clear_with_pattern_works(self):
        """
        Verify that cache.clear(pattern="foo:*") works correctly.

        This should work both before and after the fix.

        XDIST FIX: Import CacheService before patching and directly inject mock attributes.
        This avoids import-time module caching issues under pytest-xdist.
        """
        from mcp_server_langgraph.core.cache import CacheService

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"foo:1", b"foo:2"]

        # Mock L1 cache (TTLCache-like)
        mock_l1_cache = MagicMock()

        # Create CacheService with mock injection (bypass __init__)
        with patch.object(CacheService, "__init__", lambda self, **kwargs: None):
            cache = CacheService.__new__(CacheService)
            # Inject required attributes that clear() uses
            cache.redis = mock_redis
            cache.redis_available = True
            cache.l1_cache = mock_l1_cache

            # Clear with pattern
            cache.clear(pattern="foo:*")

            # Should use keys() + delete()
            mock_redis.keys.assert_called_with("foo:*")
            mock_redis.delete.assert_called_once_with(b"foo:1", b"foo:2")

            # Should NOT use flushdb
            assert not mock_redis.flushdb.called
