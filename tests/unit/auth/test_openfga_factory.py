"""
Tests for OpenFGA factory functions.

TDD: Tests written FIRST before implementation verification.
Tests the get_openfga_client() factory function added for WebSocket contexts.
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.mark.xdist_group(name="test_openfga_factory")
class TestGetOpenFGAClientFactory:
    """Tests for get_openfga_client() factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_none_when_openfga_not_configured(self) -> None:
        """
        GIVEN: OpenFGA is not configured (no API URL or store ID)
        WHEN: get_openfga_client() is called
        THEN: Returns None without error
        """
        # Reset global state
        import mcp_server_langgraph.auth.openfga as openfga_module

        openfga_module._global_openfga_client = None

        # Mock settings with no OpenFGA config
        mock_settings = MagicMock()
        mock_settings.openfga_api_url = None
        mock_settings.openfga_store_id = None

        # Use patching on the settings import
        with patch(
            "mcp_server_langgraph.auth.openfga.settings",
            mock_settings,
            create=True,
        ):
            from mcp_server_langgraph.auth.openfga import get_openfga_client

            # Reset state before test
            openfga_module._global_openfga_client = None

            result = await get_openfga_client()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_api_url_missing(self) -> None:
        """
        GIVEN: OpenFGA API URL is not set
        WHEN: get_openfga_client() is called
        THEN: Returns None
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        openfga_module._global_openfga_client = None

        mock_settings = MagicMock()
        mock_settings.openfga_api_url = None
        mock_settings.openfga_store_id = "test-store-id"

        with patch(
            "mcp_server_langgraph.auth.openfga.settings",
            mock_settings,
            create=True,
        ):
            from mcp_server_langgraph.auth.openfga import get_openfga_client

            openfga_module._global_openfga_client = None
            result = await get_openfga_client()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_store_id_missing(self) -> None:
        """
        GIVEN: OpenFGA store ID is not set
        WHEN: get_openfga_client() is called
        THEN: Returns None
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        openfga_module._global_openfga_client = None

        mock_settings = MagicMock()
        mock_settings.openfga_api_url = "http://localhost:8080"
        mock_settings.openfga_store_id = None

        with patch(
            "mcp_server_langgraph.auth.openfga.settings",
            mock_settings,
            create=True,
        ):
            from mcp_server_langgraph.auth.openfga import get_openfga_client

            openfga_module._global_openfga_client = None
            result = await get_openfga_client()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_client_on_subsequent_calls(self) -> None:
        """
        GIVEN: get_openfga_client() was called once and returned a client
        WHEN: get_openfga_client() is called again
        THEN: Returns the same cached client instance (singleton)
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        # Set a mock client as the cached instance
        mock_client = MagicMock()
        openfga_module._global_openfga_client = mock_client

        from mcp_server_langgraph.auth.openfga import get_openfga_client

        result = await get_openfga_client()

        assert result is mock_client

        # Cleanup
        openfga_module._global_openfga_client = None

    @pytest.mark.asyncio
    async def test_handles_import_error_gracefully(self) -> None:
        """
        GIVEN: Settings module fails to import
        WHEN: get_openfga_client() is called
        THEN: Returns None without raising exception
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        openfga_module._global_openfga_client = None

        with patch(
            "mcp_server_langgraph.auth.openfga.settings",
            side_effect=ImportError("Module not found"),
            create=True,
        ):
            from mcp_server_langgraph.auth.openfga import get_openfga_client

            openfga_module._global_openfga_client = None

            # Should handle gracefully - the function catches exceptions
            result = await get_openfga_client()

        # Result should be None (graceful degradation)
        assert result is None


@pytest.mark.xdist_group(name="test_openfga_factory")
class TestOpenFGAClientSingleton:
    """Tests for singleton behavior of the OpenFGA client factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_global_client_initially_none(self) -> None:
        """
        GIVEN: Fresh module import
        WHEN: Checking global client variable
        THEN: _global_openfga_client is None initially (or after reset)
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        # Reset to initial state
        openfga_module._global_openfga_client = None

        assert openfga_module._global_openfga_client is None

    def test_global_client_can_be_set(self) -> None:
        """
        GIVEN: _global_openfga_client is None
        WHEN: Setting it to a mock client
        THEN: The value is stored correctly
        """
        import mcp_server_langgraph.auth.openfga as openfga_module

        mock_client = MagicMock()
        openfga_module._global_openfga_client = mock_client

        assert openfga_module._global_openfga_client is mock_client

        # Cleanup
        openfga_module._global_openfga_client = None
