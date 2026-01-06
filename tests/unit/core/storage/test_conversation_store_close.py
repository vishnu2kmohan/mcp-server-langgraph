"""
Unit tests for ConversationStore Redis close functionality.

Tests that ConversationStore properly closes its sync Redis client.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="conversation_store_close")
class TestConversationStoreClose:
    """Tests for ConversationStore close() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_close_closes_redis_client(self) -> None:
        """Test that close() closes the sync Redis client."""
        from mcp_server_langgraph.core.storage.conversation_store import (
            ConversationStore,
        )

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.core.storage.conversation_store.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            store = ConversationStore(backend="redis", redis_url="redis://localhost:6379/2")

            # Call close
            store.close()

            # Verify Redis client was closed
            mock_client.close.assert_called_once()

    def test_close_handles_memory_backend(self) -> None:
        """Test that close() handles in-memory backend gracefully."""
        from mcp_server_langgraph.core.storage.conversation_store import (
            ConversationStore,
        )

        store = ConversationStore(backend="memory")

        # Should not raise
        store.close()

    def test_close_is_idempotent(self) -> None:
        """Test that close() can be called multiple times safely."""
        from mcp_server_langgraph.core.storage.conversation_store import (
            ConversationStore,
        )

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.core.storage.conversation_store.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            store = ConversationStore(backend="redis", redis_url="redis://localhost:6379/2")

            # Call close twice
            store.close()
            store.close()

            # Should only close once (idempotent)
            assert mock_client.close.call_count == 1

    def test_close_sets_redis_to_none(self) -> None:
        """Test that close() sets redis client to None after close."""
        from mcp_server_langgraph.core.storage.conversation_store import (
            ConversationStore,
        )

        # Create store with mocked Redis
        with patch("mcp_server_langgraph.core.storage.conversation_store.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            store = ConversationStore(backend="redis", redis_url="redis://localhost:6379/2")

            assert store._redis_client is not None

            store.close()

            assert store._redis_client is None
