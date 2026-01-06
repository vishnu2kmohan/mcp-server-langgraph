"""
Unit tests for APIKeyManager Redis close functionality.

Tests that APIKeyManager properly closes its Redis client.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="api_key_manager_close")
class TestAPIKeyManagerClose:
    """Tests for APIKeyManager aclose() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_aclose_closes_redis_client(self) -> None:
        """Test that aclose() closes the Redis client."""
        from mcp_server_langgraph.auth.api_keys import APIKeyManager

        # Create mock dependencies
        mock_keycloak = MagicMock()
        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
            cache_enabled=True,
        )

        # Call aclose
        await manager.aclose()

        # Verify Redis client was closed
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_handles_no_redis_client(self) -> None:
        """Test that aclose() handles case when no Redis client exists."""
        from mcp_server_langgraph.auth.api_keys import APIKeyManager

        mock_keycloak = MagicMock()

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=None,
            cache_enabled=False,
        )

        # Should not raise
        await manager.aclose()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self) -> None:
        """Test that aclose() can be called multiple times safely."""
        from mcp_server_langgraph.auth.api_keys import APIKeyManager

        mock_keycloak = MagicMock()
        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
            cache_enabled=True,
        )

        # Call aclose twice
        await manager.aclose()
        await manager.aclose()

        # Should only close once (idempotent)
        assert mock_redis.aclose.call_count == 1

    @pytest.mark.asyncio
    async def test_aclose_sets_redis_to_none(self) -> None:
        """Test that aclose() sets redis to None after close."""
        from mcp_server_langgraph.auth.api_keys import APIKeyManager

        mock_keycloak = MagicMock()
        mock_redis = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock(return_value=None)

        manager = APIKeyManager(
            keycloak_client=mock_keycloak,
            redis_client=mock_redis,
            cache_enabled=True,
        )

        assert manager.redis is not None

        await manager.aclose()

        assert manager.redis is None
