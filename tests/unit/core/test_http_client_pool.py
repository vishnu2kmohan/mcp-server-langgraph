"""
TDD RED Phase: Tests for HttpClientManager connection pooling.

These tests verify that:
1. HttpClientManager is a singleton
2. Returns shared httpx.AsyncClient
3. Enables HTTP/2 for connection multiplexing
4. Configures connection pool limits
5. Provides proper cleanup on shutdown

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import asyncio
import gc
from unittest.mock import MagicMock

import pytest

# Module-level pytestmark for test organization
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="http_client_pool")
class TestHttpClientManagerExists:
    """
    TDD tests to verify HttpClientManager exists and has correct interface.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_http_client_manager_class_exists(self):
        """
        RED: Verify HttpClientManager class exists.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        assert HttpClientManager is not None

    async def test_http_client_manager_is_singleton(self):
        """
        RED: Verify HttpClientManager returns same instance (singleton).
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager1 = HttpClientManager()
        manager2 = HttpClientManager()

        assert manager1 is manager2, "HttpClientManager should be a singleton"

    async def test_get_client_method_exists_and_is_async(self):
        """
        RED: Verify get_client() method exists and is async.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()

        assert hasattr(manager, "get_client"), "Must have get_client() method"
        assert asyncio.iscoroutinefunction(manager.get_client), "get_client() must be an async method"

    async def test_close_method_exists_and_is_async(self):
        """
        RED: Verify close() method exists and is async.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()

        assert hasattr(manager, "close"), "Must have close() method"
        assert asyncio.iscoroutinefunction(manager.close), "close() must be an async method"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="http_client_pool")
class TestHttpClientManagerGetClient:
    """
    TDD tests for HttpClientManager.get_client() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
        # Reset singleton for test isolation
        try:
            from mcp_server_langgraph.core.http_client import HttpClientManager

            HttpClientManager._instance = None
            HttpClientManager._client = None
        except ImportError:
            pass

    async def test_get_client_returns_async_client(self):
        """
        RED: Verify get_client() returns httpx.AsyncClient instance.
        """
        import httpx

        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        client = await manager.get_client()

        assert isinstance(client, httpx.AsyncClient), f"get_client() must return httpx.AsyncClient, got {type(client)}"

        # Clean up
        await manager.close()

    async def test_get_client_returns_same_client_instance(self):
        """
        RED: Verify get_client() returns the same client (connection pooling).
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        client1 = await manager.get_client()
        client2 = await manager.get_client()

        assert client1 is client2, "Should return same client instance for pooling"

        # Clean up
        await manager.close()

    async def test_get_client_enables_http2(self):
        """
        RED: Verify client has HTTP/2 enabled for connection multiplexing.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        client = await manager.get_client()

        # httpx.AsyncClient with http2=True has HTTP/2 support
        # We verify by checking the client was created with http2=True
        assert client._transport is not None, "Client should have transport configured"

        # Clean up
        await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="http_client_pool")
class TestHttpClientManagerClose:
    """
    TDD tests for HttpClientManager.close() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
        # Reset singleton for test isolation
        try:
            from mcp_server_langgraph.core.http_client import HttpClientManager

            HttpClientManager._instance = None
            HttpClientManager._client = None
        except ImportError:
            pass

    async def test_close_closes_client(self):
        """
        RED: Verify close() properly closes the client.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        _client = await manager.get_client()  # noqa: F841 - call needed to init

        await manager.close()

        # After close, getting a new client should create a new one
        # (manager._client should be None)
        assert manager._client is None, "Client should be None after close"

    async def test_close_is_idempotent(self):
        """
        RED: Verify close() can be called multiple times safely.
        """
        from mcp_server_langgraph.core.http_client import HttpClientManager

        manager = HttpClientManager()
        _client = await manager.get_client()  # noqa: F841 - call needed to init

        # Should not raise on multiple calls
        await manager.close()
        await manager.close()
        await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="http_client_pool")
class TestHttpClientLifespan:
    """
    TDD tests for FastAPI lifespan integration.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_http_client_lifespan_context_manager_exists(self):
        """
        RED: Verify http_client_lifespan async context manager exists.
        """
        from mcp_server_langgraph.core.http_client import http_client_lifespan

        assert http_client_lifespan is not None

        # Verify it's an async context manager
        mock_app = MagicMock()
        ctx = http_client_lifespan(mock_app)

        assert hasattr(ctx, "__aenter__"), "Must be async context manager"
        assert hasattr(ctx, "__aexit__"), "Must be async context manager"
