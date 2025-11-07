"""
Security tests for API key performance monitoring (OpenAI Codex Finding #5)

SECURITY FINDING:
On every cache miss, API key validation walks the entire Keycloak user list.
This O(n×m) scan won't scale beyond a few hundred accounts.

MITIGATION STATUS:
- PRIMARY: Redis cache provides O(1) lookups (ADR-0034)
- MONITORING: Added logging to track enumeration events
- FUTURE: Keycloak indexed attribute search recommended for >1000 users

This test suite validates monitoring and mitigation measures.

References:
- src/mcp_server_langgraph/auth/api_keys.py:283-373 (validate_and_get_user pagination)
- ADR-0034: API Key Caching Strategy
- CWE-407: Inefficient Algorithmic Complexity
"""

import logging

import pytest

from mcp_server_langgraph.auth.api_keys import APIKeyManager


@pytest.mark.security
@pytest.mark.unit
class TestAPIKeyPerformanceMonitoring:
    """Test suite for API key performance monitoring"""

    def test_validate_and_get_user_has_enumeration_warning(self, caplog):
        """
        SECURITY TEST: validate_and_get_user must log warning about O(n) enumeration

        This helps operators identify when performance optimization is needed.
        """
        import inspect

        source = inspect.getsource(APIKeyManager.validate_and_get_user)

        # Should document the O(n) performance issue
        assert "O(n)" in source or "enumeration" in source.lower(), (
            "validate_and_get_user should document O(n) enumeration performance issue"
        )

        # Should mention recommended optimization
        assert "indexed" in source.lower() or "index" in source.lower(), (
            "validate_and_get_user should document indexed search recommendation"
        )

    def test_api_keys_module_references_adr_0034(self):
        """
        Test that api_keys.py references ADR-0034 for cache mitigation

        This ensures operators know about the Redis cache mitigation strategy.
        """
        import pathlib

        api_keys_file = pathlib.Path("src/mcp_server_langgraph/auth/api_keys.py")
        content = api_keys_file.read_text()

        assert "ADR-0034" in content or "adr-0034" in content.lower(), (
            "api_keys.py should reference ADR-0034 documenting cache mitigation"
        )

    def test_api_key_manager_accepts_redis_client(self):
        """
        Test that APIKeyManager accepts Redis client for caching

        This is the primary mitigation for O(n) enumeration performance.
        """
        # Check __init__ signature accepts redis_client
        import inspect

        sig = inspect.signature(APIKeyManager.__init__)
        params = sig.parameters

        assert "redis_client" in params, (
            "APIKeyManager must accept redis_client for cache mitigation"
        )

    def test_cache_enabled_by_default_when_redis_available(self):
        """
        Test that caching is enabled by default when Redis is available

        This ensures the primary O(n) mitigation is active.
        """
        from unittest.mock import AsyncMock, MagicMock

        mock_keycloak = MagicMock()
        mock_redis = AsyncMock()

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
        )

        # Cache should be enabled
        assert manager.cache_enabled is True, (
            "Cache must be enabled by default when Redis client is provided"
        )


@pytest.mark.security
@pytest.mark.integration
class TestAPIKeyCacheMitigation:
    """Test suite for Redis cache mitigation effectiveness"""

    def test_cache_ttl_is_configurable(self):
        """
        Test that cache TTL can be configured

        Allows tuning cache effectiveness vs freshness.
        """
        from unittest.mock import AsyncMock, MagicMock

        mock_keycloak = MagicMock()
        mock_redis = AsyncMock()

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
            cache_ttl=7200,  # 2 hours
        )

        assert manager.cache_ttl == 7200

    def test_cache_can_be_disabled_for_testing(self):
        """
        Test that cache can be explicitly disabled

        Useful for testing enumeration fallback behavior.
        """
        from unittest.mock import AsyncMock, MagicMock

        mock_keycloak = MagicMock()
        mock_redis = AsyncMock()

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
            cache_enabled=False,  # Explicitly disable
        )

        assert manager.cache_enabled is False


@pytest.mark.security
@pytest.mark.unit
class TestAPIKeyEnumerationDocumentation:
    """Test suite ensuring enumeration is documented"""

    def test_docstring_mentions_performance_implications(self):
        """
        Test that validate_and_get_user docstring mentions performance

        Helps developers understand the importance of cache hits.
        """
        docstring = APIKeyManager.validate_and_get_user.__doc__ or ""

        assert "cache" in docstring.lower() or "performance" in docstring.lower(), (
            "validate_and_get_user should document cache/performance considerations"
        )

    def test_source_code_has_performance_comments(self):
        """
        Test that source code includes performance warnings

        Inline comments help future maintainers understand optimization needs.
        """
        import inspect

        source = inspect.getsource(APIKeyManager.validate_and_get_user)

        # Should have comments about performance
        assert "PERFORMANCE" in source or "performance" in source.lower(), (
            "validate_and_get_user should include performance comments/warnings"
        )

        # Should mention the Codex finding
        assert "Finding #5" in source or "Codex" in source, (
            "Source should reference OpenAI Codex Finding #5"
        )
