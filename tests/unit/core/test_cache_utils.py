"""
Unit tests for core/cache.py utility functions.

Tests cache URL building and configuration.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="cache_utils")
class TestBuildRedisUrlWithDb:
    """Test _build_redis_url_with_db function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_adds_database_to_simple_url(self):
        """Test adding database to simple Redis URL."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://localhost:6379", 2)

        assert result == "redis://localhost:6379/2"

    @pytest.mark.unit
    def test_replaces_existing_database(self):
        """Test replacing existing database number."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://localhost:6379/0", 2)

        assert result == "redis://localhost:6379/2"

    @pytest.mark.unit
    def test_handles_trailing_slash(self):
        """Test handling URL with trailing slash."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://localhost:6379/", 2)

        assert result == "redis://localhost:6379/2"

    @pytest.mark.unit
    def test_preserves_password_in_url(self):
        """Test that password is preserved in URL."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://:mypassword@localhost:6379", 3)

        assert ":mypassword@" in result
        assert result.endswith("/3")

    @pytest.mark.unit
    def test_preserves_username_and_password(self):
        """Test that username and password are preserved."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://user:pass@localhost:6379/0", 5)

        assert "user:pass@" in result
        assert result.endswith("/5")

    @pytest.mark.unit
    def test_handles_different_port(self):
        """Test handling different port numbers."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://localhost:6380", 1)

        assert ":6380/" in result
        assert result.endswith("/1")

    @pytest.mark.unit
    def test_handles_rediss_scheme(self):
        """Test handling rediss:// (SSL) scheme."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("rediss://localhost:6379", 2)

        assert result.startswith("rediss://")
        assert result.endswith("/2")

    @pytest.mark.unit
    def test_build_redis_url_with_database_zero_succeeds(self):
        """Test setting database to 0."""
        from mcp_server_langgraph.core.cache import _build_redis_url_with_db

        result = _build_redis_url_with_db("redis://localhost:6379/5", 0)

        assert result == "redis://localhost:6379/0"


@pytest.mark.xdist_group(name="cache_utils")
class TestCacheTTLs:
    """Test cache TTL configuration constants."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cache_ttls_has_expected_keys(self):
        """Test that CACHE_TTLS has all expected cache types."""
        from mcp_server_langgraph.core.cache import CACHE_TTLS

        expected_keys = [
            "auth_permission",
            "user_profile",
            "llm_response",
            "embedding",
            "prometheus_query",
            "knowledge_base",
            "feature_flag",
        ]

        for key in expected_keys:
            assert key in CACHE_TTLS

    @pytest.mark.unit
    def test_cache_ttls_are_positive_integers(self):
        """Test that all TTL values are positive integers."""
        from mcp_server_langgraph.core.cache import CACHE_TTLS

        for key, ttl in CACHE_TTLS.items():
            assert isinstance(ttl, int), f"{key} TTL is not an integer"
            assert ttl > 0, f"{key} TTL is not positive"

    @pytest.mark.unit
    def test_auth_permission_ttl_reasonable(self):
        """Test that auth permission TTL is reasonable (not too long)."""
        from mcp_server_langgraph.core.cache import CACHE_TTLS

        # Auth permissions should be cached for reasonable time (< 1 hour)
        assert CACHE_TTLS["auth_permission"] <= 3600

    @pytest.mark.unit
    def test_feature_flag_ttl_short(self):
        """Test that feature flag TTL is short for fast rollouts."""
        from mcp_server_langgraph.core.cache import CACHE_TTLS

        # Feature flags should be short for quick updates
        assert CACHE_TTLS["feature_flag"] <= 300


@pytest.mark.xdist_group(name="cache_utils")
class TestCacheLayer:
    """Test CacheLayer enum."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_cache_layer_has_l1(self):
        """Test that CacheLayer has L1."""
        from mcp_server_langgraph.core.cache import CacheLayer

        assert CacheLayer.L1 == "l1"

    @pytest.mark.unit
    def test_cache_layer_has_l2(self):
        """Test that CacheLayer has L2."""
        from mcp_server_langgraph.core.cache import CacheLayer

        assert CacheLayer.L2 == "l2"

    @pytest.mark.unit
    def test_cache_layer_has_l3(self):
        """Test that CacheLayer has L3."""
        from mcp_server_langgraph.core.cache import CacheLayer

        assert CacheLayer.L3 == "l3"
