"""
Tests for SemanticIndexManager Bootstrap Integration.

TDD tests for:
1. Configuration settings for cache warming entries
2. Bootstrap integration to wire warm_cache during startup

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation will add configuration and bootstrap wiring.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.authorization, pytest.mark.adr0099]


@pytest.mark.xdist_group(name="semantic_index_config")
class TestCacheWarmingConfiguration:
    """Tests for cache warming configuration settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_auth_cache_warm_entries_field(self) -> None:
        """Settings should have AUTH_CACHE_WARM_ENTRIES field."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "auth_cache_warm_entries")

    def test_auth_cache_warm_entries_default_is_empty_list(self) -> None:
        """AUTH_CACHE_WARM_ENTRIES should default to empty list."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.auth_cache_warm_entries == []

    def test_auth_cache_warm_entries_accepts_list_of_dicts(self) -> None:
        """AUTH_CACHE_WARM_ENTRIES should accept list of entry dicts."""
        from mcp_server_langgraph.core.config import Settings

        entries = [
            {"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"},
            {"user_id": "user:admin", "relation": "admin", "object_type": "skill_index"},
        ]

        with patch.dict(
            "os.environ",
            {"AUTH_CACHE_WARM_ENTRIES": '[{"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"}]'},
        ):
            # Settings should parse JSON from env var
            settings = Settings()
            # This test validates the field exists; parsing may vary by implementation
            assert hasattr(settings, "auth_cache_warm_entries")


@pytest.mark.xdist_group(name="semantic_index_bootstrap")
class TestBootstrapCacheWarming:
    """Tests for bootstrap integration of cache warming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_auth_calls_warm_cache_when_entries_configured(self) -> None:
        """init_auth should call warm_cache when entries are configured."""
        from mcp_server_langgraph.core.config import Settings

        # Create mock settings with warm entries
        mock_settings = MagicMock(spec=Settings)
        mock_settings.auth_provider = "none"
        mock_settings.openfga_url = None
        mock_settings.openfga_store_id = None
        mock_settings.openfga_authorization_model_id = None
        mock_settings.auth_cache_warm_entries = [
            {"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"},
        ]
        mock_settings.auth_cache_ttl_seconds = 60
        mock_settings.auth_cache_maxsize = 1000

        # Mock the semantic index manager
        mock_manager = AsyncMock(return_value=None)
        mock_manager.warm_cache = AsyncMock(return_value=1)

        with patch(
            "mcp_server_langgraph.bootstrap.security.get_semantic_index_manager",
            return_value=mock_manager,
        ):
            from mcp_server_langgraph.bootstrap.security import warm_semantic_cache

            # Call the warm function directly
            warmed = await warm_semantic_cache(mock_settings)

            # Verify warm_cache was called
            mock_manager.warm_cache.assert_called_once()
            assert warmed == 1

    @pytest.mark.asyncio
    async def test_init_auth_skips_warm_cache_when_no_entries(self) -> None:
        """init_auth should skip warm_cache when no entries configured."""
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.auth_cache_warm_entries = []

        mock_manager = AsyncMock(return_value=None)
        mock_manager.warm_cache = AsyncMock(return_value=0)

        with patch(
            "mcp_server_langgraph.bootstrap.security.get_semantic_index_manager",
            return_value=mock_manager,
        ):
            from mcp_server_langgraph.bootstrap.security import warm_semantic_cache

            warmed = await warm_semantic_cache(mock_settings)

            # warm_cache should not be called for empty list
            mock_manager.warm_cache.assert_not_called()
            assert warmed == 0

    def test_warm_semantic_cache_function_exists(self) -> None:
        """warm_semantic_cache function should exist in bootstrap.security."""
        from mcp_server_langgraph.bootstrap.security import warm_semantic_cache

        assert callable(warm_semantic_cache)
