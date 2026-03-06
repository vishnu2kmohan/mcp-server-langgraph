"""
Tests for shared Qdrant client providers (sync and async).

Tests the shared Qdrant client patterns which provide singleton clients
for both sync and async endpoints instead of creating a new client per request.

Sync client: For legacy sync code paths (if any remain)
Async client: For async endpoints (api/v1/vectors.py, dynamic_context_loader.py)

TDD Phase: RED/GREEN - Tests with implementation.
"""

import asyncio
import gc
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestQdrantSharedClient:
    """Tests for shared Qdrant client in storage/vectors/factory.py."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_shared_qdrant_client_returns_singleton(self, reset_qdrant_client):
        """get_shared_qdrant_client() should return the same client instance."""
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_qdrant_client,
        )

        with patch("qdrant_client.QdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            client1 = get_shared_qdrant_client()
            client2 = get_shared_qdrant_client()

            assert client1 is client2, "Should return same client instance"

            # QdrantClient should only be called once
            assert mock_qdrant.call_count == 1

    def test_close_qdrant_client_closes_client(self, reset_qdrant_client):
        """close_qdrant_client() should close the client and clear the reference."""
        from mcp_server_langgraph.storage.vectors.factory import (
            close_qdrant_client,
            get_shared_qdrant_client,
        )

        with patch("qdrant_client.QdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            # Get client
            client = get_shared_qdrant_client()
            assert client is mock_client

            # Close client
            close_qdrant_client()

            # Verify close was called
            mock_client.close.assert_called_once()

    def test_close_qdrant_client_is_idempotent(self, reset_qdrant_client):
        """close_qdrant_client() should be safe to call multiple times."""
        from mcp_server_langgraph.storage.vectors.factory import (
            close_qdrant_client,
            get_shared_qdrant_client,
        )

        with patch("qdrant_client.QdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            # Get client
            get_shared_qdrant_client()

            # Close multiple times - should not raise
            close_qdrant_client()
            close_qdrant_client()
            close_qdrant_client()

            # Close should only be called once (first time)
            mock_client.close.assert_called_once()

    def test_close_qdrant_client_safe_when_not_created(self, reset_qdrant_client):
        """close_qdrant_client() should be safe when no client was created."""
        from mcp_server_langgraph.storage.vectors.factory import close_qdrant_client

        # Should not raise even if no client exists
        close_qdrant_client()

    def test_concurrent_get_shared_client_creates_single(self, reset_qdrant_client):
        """Concurrent calls should create only one Qdrant client (thread safety)."""
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_qdrant_client,
        )

        with patch("qdrant_client.QdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            clients: list = []
            errors: list = []

            def get_client_thread():
                try:
                    client = get_shared_qdrant_client()
                    clients.append(client)
                except Exception as e:
                    errors.append(e)

            # Create multiple threads that call get_shared_qdrant_client simultaneously
            threads = [threading.Thread(target=get_client_thread) for _ in range(10)]

            # Start all threads
            for t in threads:
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Should have no errors
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # All clients should be the same instance
            assert len(clients) == 10
            first_client = clients[0]
            for client in clients[1:]:
                assert client is first_client, "All concurrent calls should return same client"

            # QdrantClient should only be called once
            assert mock_qdrant.call_count == 1

    def test_get_after_close_creates_new_client(self, reset_qdrant_client):
        """After close, get_shared_qdrant_client() should create a new client."""
        from mcp_server_langgraph.storage.vectors.factory import (
            close_qdrant_client,
            get_shared_qdrant_client,
        )

        with patch("qdrant_client.QdrantClient") as mock_qdrant:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_qdrant.side_effect = [mock_client1, mock_client2]

            # Get first client
            client1 = get_shared_qdrant_client()
            assert client1 is mock_client1

            # Close
            close_qdrant_client()

            # Get new client
            client2 = get_shared_qdrant_client()
            assert client2 is mock_client2

            # Should have created two clients
            assert mock_qdrant.call_count == 2


@pytest.fixture
def reset_qdrant_client():
    """Reset Qdrant client for tests that need isolation."""
    from mcp_server_langgraph.storage.vectors import factory as factory_module

    # Clear before test
    if hasattr(factory_module, "_qdrant_client"):
        factory_module._qdrant_client = None

    yield

    # Cleanup after test
    if hasattr(factory_module, "_qdrant_client"):
        factory_module._qdrant_client = None


@pytest.fixture
def reset_async_qdrant_client():
    """Reset async Qdrant client for tests that need isolation."""
    from mcp_server_langgraph.storage.vectors import factory as factory_module

    # Clear before test
    if hasattr(factory_module, "_async_qdrant_client"):
        factory_module._async_qdrant_client = None

    yield

    # Cleanup after test
    if hasattr(factory_module, "_async_qdrant_client"):
        factory_module._async_qdrant_client = None


@pytest.mark.unit
class TestAsyncQdrantSharedClient:
    """Tests for shared async Qdrant client in storage/vectors/factory.py."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_shared_async_qdrant_client_returns_singleton(self, reset_async_qdrant_client):
        """get_shared_async_qdrant_client() should return the same client instance."""
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_async_qdrant_client,
        )

        with patch("qdrant_client.AsyncQdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            client1 = await get_shared_async_qdrant_client()
            client2 = await get_shared_async_qdrant_client()

            assert client1 is client2, "Should return same client instance"

            # AsyncQdrantClient should only be called once
            assert mock_qdrant.call_count == 1

    @pytest.mark.asyncio
    async def test_aclose_async_qdrant_client_closes_client(self, reset_async_qdrant_client):
        """aclose_async_qdrant_client() should close the client and clear the reference."""
        from mcp_server_langgraph.storage.vectors.factory import (
            aclose_async_qdrant_client,
            get_shared_async_qdrant_client,
        )

        with patch("qdrant_client.AsyncQdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_client.close = AsyncMock(return_value=None)
            mock_qdrant.return_value = mock_client

            # Get client
            client = await get_shared_async_qdrant_client()
            assert client is mock_client

            # Close client
            await aclose_async_qdrant_client()

            # Verify close was called
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_async_qdrant_client_is_idempotent(self, reset_async_qdrant_client):
        """aclose_async_qdrant_client() should be safe to call multiple times."""
        from mcp_server_langgraph.storage.vectors.factory import (
            aclose_async_qdrant_client,
            get_shared_async_qdrant_client,
        )

        with patch("qdrant_client.AsyncQdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_client.close = AsyncMock(return_value=None)
            mock_qdrant.return_value = mock_client

            # Get client
            await get_shared_async_qdrant_client()

            # Close multiple times - should not raise
            await aclose_async_qdrant_client()
            await aclose_async_qdrant_client()
            await aclose_async_qdrant_client()

            # Close should only be called once (first time)
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_async_qdrant_client_safe_when_not_created(self, reset_async_qdrant_client):
        """aclose_async_qdrant_client() should be safe when no client was created."""
        from mcp_server_langgraph.storage.vectors.factory import (
            aclose_async_qdrant_client,
        )

        # Should not raise even if no client exists
        await aclose_async_qdrant_client()

    @pytest.mark.asyncio
    async def test_concurrent_get_shared_async_client_creates_single(self, reset_async_qdrant_client):
        """Concurrent async calls should create only one Qdrant client (async safety)."""
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_async_qdrant_client,
        )

        with patch("qdrant_client.AsyncQdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            # Create multiple concurrent async calls
            tasks = [get_shared_async_qdrant_client() for _ in range(10)]
            clients = await asyncio.gather(*tasks)

            # All clients should be the same instance
            assert len(clients) == 10
            first_client = clients[0]
            for client in clients[1:]:
                assert client is first_client, "All concurrent calls should return same client"

            # AsyncQdrantClient should only be called once
            assert mock_qdrant.call_count == 1

    @pytest.mark.asyncio
    async def test_get_after_aclose_creates_new_client(self, reset_async_qdrant_client):
        """After aclose, get_shared_async_qdrant_client() should create a new client."""
        from mcp_server_langgraph.storage.vectors.factory import (
            aclose_async_qdrant_client,
            get_shared_async_qdrant_client,
        )

        with patch("qdrant_client.AsyncQdrantClient") as mock_qdrant:
            mock_client1 = MagicMock()
            mock_client1.close = AsyncMock(return_value=None)
            mock_client2 = MagicMock()
            mock_client2.close = AsyncMock(return_value=None)
            mock_qdrant.side_effect = [mock_client1, mock_client2]

            # Get first client
            client1 = await get_shared_async_qdrant_client()
            assert client1 is mock_client1

            # Close
            await aclose_async_qdrant_client()

            # Get new client
            client2 = await get_shared_async_qdrant_client()
            assert client2 is mock_client2

            # Should have created two clients
            assert mock_qdrant.call_count == 2

    @pytest.mark.asyncio
    async def test_async_client_uses_settings(self, reset_async_qdrant_client):
        """get_shared_async_qdrant_client() should use settings for configuration."""
        from mcp_server_langgraph.storage.vectors.factory import (
            get_shared_async_qdrant_client,
        )

        with (
            patch("qdrant_client.AsyncQdrantClient") as mock_qdrant,
            patch("mcp_server_langgraph.core.config.settings") as mock_settings,
        ):
            mock_settings.qdrant_url = "http://test-qdrant:6333"
            mock_settings.qdrant_port = 6333

            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            await get_shared_async_qdrant_client()

            # Verify client was created with settings
            mock_qdrant.assert_called_once_with(
                url="http://test-qdrant:6333",
                port=6333,
            )
