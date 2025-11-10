"""
TDD Tests for L2 Cache Redis Configuration

Tests validate that CacheService properly uses secure Redis settings
(redis_url, redis_password, redis_ssl) instead of just redis_host and redis_port.

Critical bug this catches:
- cache.py:94-120 ignores settings.redis_url, settings.redis_password, settings.redis_ssl
- This causes L2 cache to silently fall back to L1-only in production

The correct pattern is demonstrated in dependencies.py:116-125 (API key manager).
"""

import gc
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
@pytest.mark.xdist_group(name="unit_cache_redis_config_tests")
class TestCacheServiceRedisConfiguration:
    """Test that CacheService uses proper Redis configuration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cache_service_uses_redis_url_pattern(self):
        """
        CRITICAL: CacheService must use redis.from_url() with full config.

        Bug: cache.py:95-106 uses redis.Redis(host=..., port=...) directly,
        ignoring settings.redis_url, settings.redis_password, and settings.redis_ssl.

        Fix: Use redis.from_url() pattern like API key manager does.
        """
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_redis_instance

            # Act: Create cache service with full configuration
            _cache = CacheService(
                redis_url="redis://secure-redis:6379",
                redis_db=2,
                redis_password="secure-password",
                redis_ssl=True,
            )

            # Assert: Should use redis.from_url() with properly constructed URL
            mock_redis_module.from_url.assert_called_once()
            call_args = mock_redis_module.from_url.call_args

            # Verify URL is properly constructed (not just string concat)
            actual_url = call_args[0][0]
            assert actual_url == "redis://secure-redis:6379/2"

            # Verify password and SSL are passed
            assert call_args[1]["password"] == "secure-password"
            assert call_args[1]["ssl"] is True

            # Verify cache is available
            assert hasattr(_cache, "redis")
            assert _cache.redis_available is True

    def test_cache_service_honors_redis_password_and_ssl(self):
        """
        Test that password and SSL settings are properly passed to Redis client.

        This is the pattern used correctly in dependencies.py:189-220 for
        API key manager that should be replicated for L2 cache.
        """
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_instance = Mock()
            mock_instance.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_instance

            # Act: Create cache with secure settings
            _cache = CacheService(
                redis_url="redis://secure-host:6380",
                redis_db=2,
                redis_password="secret-pass",
                redis_ssl=True,
            )

            # Assert: redis.from_url() called with proper URL and settings
            mock_redis_module.from_url.assert_called_once()
            call_args = mock_redis_module.from_url.call_args

            # Verify URL construction
            assert call_args[0][0] == "redis://secure-host:6380/2"

            # Verify password and SSL are passed
            assert call_args[1]["password"] == "secret-pass"
            assert call_args[1]["ssl"] is True
            assert call_args[1]["decode_responses"] is False  # Binary mode for pickle

            assert _cache.redis_available is True

    def test_cache_service_falls_back_to_l1_when_redis_unavailable(self):
        """
        Test graceful degradation when Redis is unavailable.

        Cache should fall back to L1-only instead of crashing.
        """
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis:
            # Simulate Redis connection failure
            mock_redis.side_effect = Exception("Connection refused")

            # Act: Create cache (should not crash)
            _cache = CacheService(redis_url="redis://localhost:6379", redis_db=2)

            # Assert: L2 cache disabled, L1 still works
            assert _cache.redis_available is False

            # Cache operations should still work with L1
            _cache.set("test_key", "test_value", level="l1")
            assert _cache.get("test_key", level="l1") == "test_value"


@pytest.mark.unit
@pytest.mark.xdist_group(name="unit_cache_redis_config_tests")
class TestCacheServiceComparison:
    """
    Compare CacheService pattern with APIKeyManager pattern.

    Demonstrates that APIKeyManager has correct pattern that CacheService should follow.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_api_key_manager_redis_pattern_is_correct(self):
        """
        Document the CORRECT pattern from dependencies.py:116-125.

        This is what CacheService should do:
        redis.from_url(f"{redis_url}/{db}", password=..., ssl=..., decode_responses=True)
        """
        from mcp_server_langgraph.core.dependencies import get_api_key_manager

        with patch("mcp_server_langgraph.core.dependencies.settings") as mock_settings:
            mock_settings.api_key_cache_enabled = True
            mock_settings.redis_url = "redis://secure-redis:6379"
            mock_settings.redis_password = "password123"
            mock_settings.redis_ssl = True
            mock_settings.api_key_cache_db = 2
            mock_settings.api_key_cache_ttl = 3600
            mock_settings.keycloak_server_url = "http://localhost:8082"
            mock_settings.keycloak_realm = "test"
            mock_settings.keycloak_client_id = "test"
            mock_settings.keycloak_client_secret = "secret"
            mock_settings.keycloak_admin_username = "admin"
            mock_settings.keycloak_admin_password = "admin-password"

            with patch("redis.asyncio.from_url") as mock_from_url:
                mock_from_url.return_value = Mock()

                # Act
                _manager = get_api_key_manager()

                # Assert: Uses redis.from_url with full config
                mock_from_url.assert_called_once_with(
                    "redis://secure-redis:6379/2",
                    password="password123",
                    ssl=True,
                    decode_responses=True,
                )
                assert _manager is not None  # Use variable to avoid F841

    def test_cache_service_should_use_same_pattern(self):
        """
        Test that after fix, CacheService uses same pattern as APIKeyManager.

        Expected behavior after fix:
        - Parse redis_url from settings
        - Append database number to URL correctly using urllib.parse
        - Pass password and ssl parameters

        This test verifies the fix for the Redis URL construction bug where
        simple string concatenation (redis_url + '/' + db) creates malformed URLs:
        - redis://localhost:6379/0 + /2 = redis://localhost:6379/0/2 (wrong!)
        - redis://localhost:6379/ + /2 = redis://localhost:6379//2 (wrong!)

        The correct approach uses urllib.parse to replace the path component.
        """
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            # Setup mock
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_redis_instance

            # Test various Redis URL formats
            test_cases = [
                # (input_url, expected_url_with_db)
                ("redis://localhost:6379", "redis://localhost:6379/2"),
                ("redis://localhost:6379/", "redis://localhost:6379/2"),
                ("redis://localhost:6379/0", "redis://localhost:6379/2"),  # Replace existing DB
                ("redis://:password@host:6380", "redis://:password@host:6380/2"),
                ("rediss://secure-host:6379", "rediss://secure-host:6379/2"),  # SSL scheme
            ]

            for input_url, expected_url in test_cases:
                mock_redis_module.from_url.reset_mock()

                # Act: Create cache service
                cache = CacheService(
                    redis_url=input_url,
                    redis_db=2,
                    redis_password="test-password",
                    redis_ssl=True,
                )

                # Assert: redis.from_url called with properly constructed URL
                mock_redis_module.from_url.assert_called_once()
                actual_url = mock_redis_module.from_url.call_args[0][0]

                assert actual_url == expected_url, (
                    f"URL construction failed:\n"
                    f"  Input: {input_url}\n"
                    f"  Expected: {expected_url}\n"
                    f"  Actual: {actual_url}\n"
                    f"  This indicates the bug is not fixed - still using string concatenation"
                )

                # Verify password and SSL are passed
                call_kwargs = mock_redis_module.from_url.call_args[1]
                assert call_kwargs["password"] == "test-password"
                assert call_kwargs["ssl"] is True
                assert cache.redis_available is True  # Use cache variable


@pytest.mark.integration
@pytest.mark.xdist_group(name="unit_cache_redis_config_tests")
class TestCacheServiceProductionScenario:
    """Integration test simulating production Redis configuration"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cache_with_production_redis_url(self):
        """
        Smoke test: Cache should work with production-style Redis URL.

        Example production URLs:
        - redis://redis-master.default.svc.cluster.local:6379
        - redis://:password@redis-host:6380
        - rediss://secure-redis.example.com:6380 (SSL)

        Verifies that the URL parsing correctly handles:
        - Embedded passwords in URL (redis://:password@host:port)
        - Cluster DNS names
        - SSL schemes (rediss://)
        """
        from mcp_server_langgraph.core.cache import CacheService

        # Test with mock to avoid actual Redis connection
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_instance = Mock()
            mock_instance.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_instance

            # Test various production URL formats
            test_cases = [
                # (redis_url, expected_url_with_db)
                ("redis://:secure-password@redis-master:6379", "redis://:secure-password@redis-master:6379/2"),
                (
                    "redis://redis-master.default.svc.cluster.local:6379",
                    "redis://redis-master.default.svc.cluster.local:6379/2",
                ),
                ("rediss://secure-redis.example.com:6380", "rediss://secure-redis.example.com:6380/2"),
            ]

            for redis_url, expected_url in test_cases:
                mock_redis_module.from_url.reset_mock()

                # Act: Simulate production config
                _cache = CacheService(
                    redis_url=redis_url,
                    redis_db=2,
                )

                # Assert: Should be available with L2 enabled
                mock_redis_module.from_url.assert_called_once()
                actual_url = mock_redis_module.from_url.call_args[0][0]
                assert actual_url == expected_url, f"Failed for {redis_url}: expected {expected_url}, got {actual_url}"
                assert _cache.redis_available is True
