"""
Unit tests for SessionStore close functionality.

Tests that RedisSessionStore properly closes its async Redis client.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


class TestSessionStoreClose:
    """Tests for SessionStore aclose() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_redis_session_store_aclose_closes_redis_client(self) -> None:
        """Test that RedisSessionStore.aclose() closes the async Redis client."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.auth.session.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock(return_value=None)
            mock_redis_module.from_url.return_value = mock_client

            store = RedisSessionStore(
                redis_url="redis://localhost:6379/0",
                default_ttl_seconds=3600,
            )

            # Call aclose
            await store.aclose()

            # Verify Redis client was closed
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_session_store_aclose_is_idempotent(self) -> None:
        """Test that aclose() can be called multiple times safely."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.auth.session.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock(return_value=None)
            mock_redis_module.from_url.return_value = mock_client

            store = RedisSessionStore(
                redis_url="redis://localhost:6379/0",
                default_ttl_seconds=3600,
            )

            # Call aclose twice
            await store.aclose()
            await store.aclose()

            # Should only close once (idempotent)
            assert mock_client.aclose.call_count == 1

    @pytest.mark.asyncio
    async def test_redis_session_store_aclose_sets_redis_to_none(self) -> None:
        """Test that aclose() sets redis client to None after close."""
        from mcp_server_langgraph.auth.session import RedisSessionStore

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.auth.session.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock(return_value=None)
            mock_redis_module.from_url.return_value = mock_client

            store = RedisSessionStore(
                redis_url="redis://localhost:6379/0",
                default_ttl_seconds=3600,
            )

            assert store.redis is not None

            await store.aclose()

            assert store.redis is None

    @pytest.mark.asyncio
    async def test_inmemory_session_store_aclose_is_noop(self) -> None:
        """Test that InMemorySessionStore.aclose() is a no-op."""
        from mcp_server_langgraph.auth.session import InMemorySessionStore

        store = InMemorySessionStore()

        # Should not raise
        await store.aclose()
        # Should be callable multiple times
        await store.aclose()

    @pytest.mark.asyncio
    async def test_session_store_abc_has_aclose_method(self) -> None:
        """Test that SessionStore ABC defines aclose() method."""
        from mcp_server_langgraph.auth.session import SessionStore

        # Verify aclose is defined in SessionStore
        assert hasattr(SessionStore, "aclose")
        assert callable(getattr(SessionStore, "aclose", None))

        # Verify it's an abstract method
        assert "aclose" in SessionStore.__abstractmethods__
