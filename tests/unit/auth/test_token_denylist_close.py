"""
Unit tests for TokenDenylist Redis close functionality.

Tests that RedisTokenDenylist properly closes its Redis client.
"""

import gc
from unittest.mock import AsyncMock

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="token_denylist_close")
class TestRedisTokenDenylistClose:
    """Tests for RedisTokenDenylist aclose() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_aclose_closes_redis_client(self) -> None:
        """Test that aclose() closes the Redis client."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        denylist = RedisTokenDenylist(redis_client=mock_redis)

        # Call aclose
        await denylist.aclose()

        # Verify Redis client was closed
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self) -> None:
        """Test that aclose() can be called multiple times safely."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        denylist = RedisTokenDenylist(redis_client=mock_redis)

        # Call aclose twice
        await denylist.aclose()
        await denylist.aclose()

        # Should only close once (idempotent)
        assert mock_redis.aclose.call_count == 1

    @pytest.mark.asyncio
    async def test_aclose_sets_redis_to_none(self) -> None:
        """Test that aclose() sets redis to None after close."""
        from mcp_server_langgraph.auth.token_denylist import RedisTokenDenylist

        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        denylist = RedisTokenDenylist(redis_client=mock_redis)

        assert denylist.redis is not None

        await denylist.aclose()

        assert denylist.redis is None


@pytest.mark.xdist_group(name="token_denylist_close")
class TestInMemoryTokenDenylistClose:
    """Tests for InMemoryTokenDenylist aclose() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_aclose_does_nothing(self) -> None:
        """Test that aclose() is a no-op for in-memory implementation."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()

        # Should not raise
        await denylist.aclose()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self) -> None:
        """Test that aclose() can be called multiple times safely."""
        from mcp_server_langgraph.auth.token_denylist import InMemoryTokenDenylist

        denylist = InMemoryTokenDenylist()

        # Should not raise when called multiple times
        await denylist.aclose()
        await denylist.aclose()
