"""
Consolidated FastAPI Dependency Providers.

This module provides all Depends() providers using the request-state pattern.
Dependencies are initialized once at app startup and stored in app.state,
then accessed via these dependency functions in route handlers.

Benefits:
- No global singletons (testable, parallel-safe)
- Async initialization at startup (no cold-start latency)
- Request-scoped access (proper FastAPI idiom)
- Centralized dependency wiring

Usage:
    from mcp_server_langgraph.api.deps import get_openfga_client, get_http_client

    @router.get("/resource")
    async def get_resource(
        openfga: OpenFGAClient | None = Depends(get_openfga_client),
        http_client: httpx.AsyncClient = Depends(get_http_client),
    ):
        ...
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import TYPE_CHECKING

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.core.config import Settings

if TYPE_CHECKING:
    from mcp_server_langgraph.audit.service import UnifiedAuditService
    from mcp_server_langgraph.auth.api_keys import APIKeyManager
    from mcp_server_langgraph.auth.openfga import OpenFGAClient
    from mcp_server_langgraph.core.http_client import HttpClientManager
    from mcp_server_langgraph.observability.query.backends.tempo import TempoTracingClient


# ==============================================================================
# Settings Provider (cached, not request-scoped)
# ==============================================================================


@lru_cache
def get_settings() -> Settings:
    """
    Get Settings instance (cached singleton via lru_cache).

    This is the only dependency that uses caching rather than request-state,
    as Settings are immutable and environment-derived.

    Returns:
        Settings instance

    Example:
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_settings)):
            return {"environment": settings.environment}
    """
    return Settings()


# ==============================================================================
# Request-State Providers (initialized at startup, accessed per-request)
# ==============================================================================


def get_openfga_client(request: Request) -> "OpenFGAClient | None":
    """
    Get OpenFGA client from FastAPI request state.

    The client is initialized once during app lifespan startup and stored
    in app.state.openfga_client. This eliminates cold-start latency and
    ensures proper async initialization.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        OpenFGAClient if configured and initialized, None otherwise

    Example:
        @router.get("/resource")
        async def get_resource(
            openfga: OpenFGAClient | None = Depends(get_openfga_client),
        ):
            if openfga:
                allowed = await openfga.check_permission(...)
    """
    return getattr(request.app.state, "openfga_client", None)


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Get shared HTTP client from FastAPI request state.

    Provides access to the shared httpx.AsyncClient with HTTP/2 and
    connection pooling initialized at app startup.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        Shared httpx.AsyncClient instance

    Raises:
        RuntimeError: If HTTP client manager not initialized

    Example:
        @router.get("/external-data")
        async def fetch_external_data(
            http_client: httpx.AsyncClient = Depends(get_http_client),
        ):
            response = await http_client.get("https://api.example.com/data")
            return response.json()
    """
    http_client_manager: HttpClientManager | None = getattr(request.app.state, "http_client_manager", None)
    if http_client_manager is None:
        msg = "HTTP client manager not initialized. Ensure app lifespan is configured."
        raise RuntimeError(msg)

    return await http_client_manager.get_client()


def get_audit_service(request: Request) -> "UnifiedAuditService | None":
    """
    Get audit service from FastAPI request state.

    The audit service is initialized at startup with the appropriate
    repository (Postgres in production, in-memory for dev/test).

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        UnifiedAuditService if initialized, None otherwise

    Example:
        @router.post("/action")
        async def perform_action(
            audit: UnifiedAuditService | None = Depends(get_audit_service),
        ):
            if audit:
                await audit.log_event(...)
    """
    return getattr(request.app.state, "audit_service", None)


def get_api_key_manager(request: Request) -> "APIKeyManager | None":
    """
    Get API key manager from FastAPI request state.

    The API key manager is initialized at startup with Keycloak client
    and optional Redis cache for O(1) API key lookups.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        APIKeyManager if initialized, None otherwise

    Example:
        @router.post("/users/{user_id}/api-key")
        async def generate_api_key(
            user_id: str,
            api_key_manager: APIKeyManager | None = Depends(get_api_key_manager),
        ):
            if api_key_manager:
                result = await api_key_manager.create_api_key(user_id, "Admin Generated")
                return result
    """
    return getattr(request.app.state, "api_key_manager", None)


def get_tempo_client(request: Request) -> "TempoTracingClient | None":
    """
    Get Tempo tracing client from FastAPI request state.

    The Tempo client is initialized at startup for querying distributed traces
    from Grafana Tempo. Used for session trace retrieval.

    Args:
        request: FastAPI Request object (injected via Depends)

    Returns:
        TempoTracingClient if initialized, None otherwise

    Example:
        @router.get("/sessions/{session_id}/trace")
        async def get_session_trace(
            session_id: str,
            tempo: TempoTracingClient | None = Depends(get_tempo_client),
        ):
            if tempo:
                traces = await tempo.search_traces(tags={"session_id": session_id})
    """
    return getattr(request.app.state, "tempo_client", None)


# ==============================================================================
# Database Session Provider
# ==============================================================================


async def get_db_session(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session for dependency injection.

    Creates a new session for each request and handles commit/rollback/close
    automatically.

    Args:
        settings: Settings instance (injected via Depends)

    Yields:
        AsyncSession: Database session for the request

    Example:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()
    """
    from mcp_server_langgraph.database.session import get_session_maker

    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured. Set the DATABASE_URL environment variable.")

    session_maker = get_session_maker(database_url)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==============================================================================
# Cache Management (for testing)
# ==============================================================================


def clear_deps_cache() -> None:
    """
    Clear all cached dependencies.

    This should only be used in tests to ensure clean state between test runs.

    Usage:
        from mcp_server_langgraph.api.deps import clear_deps_cache

        def setup_function():
            clear_deps_cache()
    """
    get_settings.cache_clear()
