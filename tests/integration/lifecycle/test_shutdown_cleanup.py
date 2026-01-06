"""
Tests for application shutdown cleanup.

Tests the cleanup_all_clients() function which handles proper disposal of:
- PostgreSQL engine registry
- CacheService Redis clients (sync + async)
- Qdrant shared client
- APIKeyManager Redis client
- TokenDenylist Redis client
- ConversationStore Redis client

TDD Phase: RED/GREEN - Tests with implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="lifecycle_cleanup")
@pytest.mark.integration
class TestShutdownCleanup:
    """Tests for cleanup_all_clients() in lifecycle/cleanup.py."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_disposes_postgres_engines(self):
        """cleanup_all_clients() should call dispose_all_engines()."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
            ) as mock_dispose,
            patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client") as mock_close_qdrant,
        ):
            # Setup mocks
            mock_cache = MagicMock()
            mock_cache.aclose = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            # Call cleanup
            await cleanup_all_clients()

            # Verify dispose_all_engines was called
            mock_dispose.assert_called_once()
            # Verify qdrant cleanup was attempted
            mock_close_qdrant.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_cache_service(self):
        """cleanup_all_clients() should close CacheService Redis clients."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
            ),
            patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
        ):
            # Setup mock cache
            mock_cache = MagicMock()
            mock_cache.aclose = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            # Call cleanup
            await cleanup_all_clients()

            # Verify both sync and async close were called
            mock_cache.close.assert_called_once()
            mock_cache.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_qdrant_client(self):
        """cleanup_all_clients() should close Qdrant client."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
            ),
            patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client") as mock_close_qdrant,
        ):
            # Setup mock cache
            mock_cache = MagicMock()
            mock_cache.aclose = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            # Call cleanup
            await cleanup_all_clients()

            # Verify close_qdrant_client was called
            mock_close_qdrant.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_handles_missing_clients_gracefully(self):
        """cleanup_all_clients() should not raise if clients don't exist."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch(
                "mcp_server_langgraph.core.cache.get_cache",
                side_effect=Exception("Cache not initialized"),
            ),
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
                side_effect=Exception("No engines"),
            ),
            patch(
                "mcp_server_langgraph.storage.vectors.factory.close_qdrant_client",
                side_effect=Exception("No Qdrant client"),
            ),
        ):
            # Should not raise even if all clients fail
            await cleanup_all_clients()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_handles_none_cache_gracefully(self):
        """cleanup_all_clients() should handle None cache return."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
            ),
            patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
        ):
            # Return None for cache
            mock_get_cache.return_value = None

            # Should not raise
            await cleanup_all_clients()

    @pytest.mark.asyncio
    async def test_cleanup_order_is_cache_then_postgres_then_qdrant(self):
        """Cleanup should happen in order: cache, postgres, qdrant."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        call_order = []

        def track_cache_close():
            call_order.append("cache_close")

        async def track_cache_aclose():
            call_order.append("cache_aclose")

        async def track_dispose():
            call_order.append("postgres_dispose")

        def track_qdrant_close():
            call_order.append("qdrant_close")

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
                side_effect=track_dispose,
            ),
            patch(
                "mcp_server_langgraph.storage.vectors.factory.close_qdrant_client",
                side_effect=track_qdrant_close,
            ),
        ):
            # Setup mock cache with order tracking
            mock_cache = MagicMock()
            mock_cache.close = MagicMock(side_effect=track_cache_close)
            mock_cache.aclose = AsyncMock(side_effect=track_cache_aclose)
            mock_get_cache.return_value = mock_cache

            # Call cleanup
            await cleanup_all_clients()

            # Verify order: cache first (sync then async), postgres, qdrant
            assert call_order == [
                "cache_close",
                "cache_aclose",
                "postgres_dispose",
                "qdrant_close",
            ]

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_api_key_manager(self):
        """cleanup_all_clients() should close APIKeyManager Redis client."""
        from mcp_server_langgraph.core import dependencies as deps_module
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        # Setup mock APIKeyManager
        mock_manager = MagicMock()
        mock_manager.aclose = AsyncMock(return_value=None)

        # Save original value
        original = deps_module._api_key_manager
        deps_module._api_key_manager = mock_manager

        try:
            with (
                patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
                patch(
                    "mcp_server_langgraph.database.session.dispose_all_engines",
                    new_callable=AsyncMock,
                ),
                patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
            ):
                mock_cache = MagicMock()
                mock_cache.aclose = AsyncMock(return_value=None)
                mock_get_cache.return_value = mock_cache

                await cleanup_all_clients()

                # Verify APIKeyManager.aclose was called
                mock_manager.aclose.assert_called_once()
        finally:
            deps_module._api_key_manager = original

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_token_denylist(self):
        """cleanup_all_clients() should close TokenDenylist Redis client."""
        from mcp_server_langgraph.core import dependencies as deps_module
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        # Setup mock TokenDenylist
        mock_denylist = MagicMock()
        mock_denylist.aclose = AsyncMock(return_value=None)

        # Save original value
        original = deps_module._token_denylist
        deps_module._token_denylist = mock_denylist

        try:
            with (
                patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
                patch(
                    "mcp_server_langgraph.database.session.dispose_all_engines",
                    new_callable=AsyncMock,
                ),
                patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
            ):
                mock_cache = MagicMock()
                mock_cache.aclose = AsyncMock(return_value=None)
                mock_get_cache.return_value = mock_cache

                await cleanup_all_clients()

                # Verify TokenDenylist.aclose was called
                mock_denylist.aclose.assert_called_once()
        finally:
            deps_module._token_denylist = original

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_conversation_store(self):
        """cleanup_all_clients() should close ConversationStore Redis client."""
        from mcp_server_langgraph.core.storage import conversation_store as conv_module
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        # Setup mock ConversationStore
        mock_store = MagicMock()
        mock_store.close = MagicMock()

        # Save original value
        original = conv_module._conversation_store
        conv_module._conversation_store = mock_store

        try:
            with (
                patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
                patch(
                    "mcp_server_langgraph.database.session.dispose_all_engines",
                    new_callable=AsyncMock,
                ),
                patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
            ):
                mock_cache = MagicMock()
                mock_cache.aclose = AsyncMock(return_value=None)
                mock_get_cache.return_value = mock_cache

                await cleanup_all_clients()

                # Verify ConversationStore.close was called
                mock_store.close.assert_called_once()
        finally:
            conv_module._conversation_store = original

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_session_service(self):
        """cleanup_all_clients() should close Session service clients."""
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        with (
            patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
            patch(
                "mcp_server_langgraph.database.session.dispose_all_engines",
                new_callable=AsyncMock,
            ),
            patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
            patch(
                "mcp_server_langgraph.api.v1.sessions.cleanup_session_service",
                new_callable=AsyncMock,
            ) as mock_session_cleanup,
        ):
            mock_cache = MagicMock()
            mock_cache.aclose = AsyncMock(return_value=None)
            mock_get_cache.return_value = mock_cache

            await cleanup_all_clients()

            # Verify cleanup_session_service was called
            mock_session_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all_clients_closes_auth_session_store(self):
        """cleanup_all_clients() should close auth session store."""
        from mcp_server_langgraph.auth import session as session_module
        from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

        # Setup mock session store
        mock_store = MagicMock()
        mock_store.aclose = AsyncMock(return_value=None)

        # Save original value
        original = session_module._session_store
        session_module._session_store = mock_store

        try:
            with (
                patch("mcp_server_langgraph.core.cache.get_cache") as mock_get_cache,
                patch(
                    "mcp_server_langgraph.database.session.dispose_all_engines",
                    new_callable=AsyncMock,
                ),
                patch("mcp_server_langgraph.storage.vectors.factory.close_qdrant_client"),
            ):
                mock_cache = MagicMock()
                mock_cache.aclose = AsyncMock(return_value=None)
                mock_get_cache.return_value = mock_cache

                await cleanup_all_clients()

                # Verify auth session store aclose was called
                mock_store.aclose.assert_called_once()
        finally:
            session_module._session_store = original
