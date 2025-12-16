"""
HTTP Client Manager with Connection Pooling.

Provides:
- Singleton HttpClientManager for shared httpx.AsyncClient
- HTTP/2 enabled for connection multiplexing
- Connection pool limits (100 keep-alive, 200 max)
- FastAPI lifespan integration for cleanup

See sync-to-async conversion plan for design rationale.
"""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import httpx

from mcp_server_langgraph.observability.telemetry import logger


class HttpClientManager:
    """
    Singleton manager for shared httpx.AsyncClient.

    Provides HTTP/2 enabled connection pooling for all HTTP operations
    in the application. Uses singleton pattern to ensure a single
    connection pool is shared across all components.

    Usage:
        manager = HttpClientManager()
        client = await manager.get_client()
        response = await client.get("https://api.example.com/data")

        # On application shutdown
        await manager.close()
    """

    _instance: "HttpClientManager | None" = None
    _client: httpx.AsyncClient | None = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> "HttpClientManager":
        """Singleton pattern - returns same instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance

    async def get_client(self) -> httpx.AsyncClient:
        """
        Get the shared AsyncClient with connection pooling.

        Creates client lazily on first call with:
        - HTTP/2 enabled for connection multiplexing
        - Connection pool limits (100 keep-alive, 200 max)
        - Reasonable timeouts

        Returns:
            Shared httpx.AsyncClient instance
        """
        if self._client is None:
            # Use lock to prevent race condition during client creation
            if self._lock is None:
                self._lock = asyncio.Lock()

            async with self._lock:
                # Double-check after acquiring lock
                if self._client is None:
                    # Configure connection pool limits
                    limits = httpx.Limits(
                        max_keepalive_connections=100,
                        max_connections=200,
                        keepalive_expiry=30.0,  # 30 seconds keepalive
                    )

                    # Create client with HTTP/2 and connection pooling
                    self._client = httpx.AsyncClient(
                        http2=True,  # Enable HTTP/2 for multiplexing
                        limits=limits,
                        timeout=httpx.Timeout(
                            connect=5.0,
                            read=30.0,
                            write=30.0,
                            pool=10.0,
                        ),
                        follow_redirects=True,
                    )

                    logger.info(
                        "HTTP client pool initialized",
                        extra={
                            "http2": True,
                            "max_keepalive": 100,
                            "max_connections": 200,
                        },
                    )

        return self._client

    async def close(self) -> None:
        """
        Close the HTTP client and release connections.

        Safe to call multiple times (idempotent).
        """
        if self._client is not None:
            try:
                await self._client.aclose()
                logger.info("HTTP client pool closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
            finally:
                self._client = None


@asynccontextmanager
async def http_client_lifespan(app: Any) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager for HTTP client pool.

    Ensures HTTP client is properly closed on application shutdown.

    Usage:
        from fastapi import FastAPI
        from mcp_server_langgraph.core.http_client import http_client_lifespan

        app = FastAPI(lifespan=http_client_lifespan)

    Args:
        app: FastAPI application instance
    """
    # Startup: nothing needed (client is lazy-initialized)
    yield

    # Shutdown: close the HTTP client pool
    manager = HttpClientManager()
    await manager.close()


def get_http_client_manager() -> HttpClientManager:
    """
    Get the global HttpClientManager instance.

    Returns:
        HttpClientManager singleton instance
    """
    return HttpClientManager()
