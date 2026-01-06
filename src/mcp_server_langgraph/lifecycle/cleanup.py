"""
Shared lifecycle cleanup helpers for all FastAPI app variants.

This module provides centralized cleanup functions that are invoked from
both FastAPI lifespan handlers:
- mcp/server_streamable.py (Streamable HTTP - Docker Compose uses this)
- infrastructure/app_factory.py (stdio variant)

Having cleanup in one place ensures consistent behavior across all app variants.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def cleanup_all_clients() -> None:
    """
    Cleanup all database and service clients.

    Call from FastAPI lifespan shutdown in:
    - mcp/server_streamable.py (Streamable HTTP) - CRITICAL
    - infrastructure/app_factory.py (stdio)
    - authz_proxy/server.py (optional - already has OpenFGA cleanup)

    Safe to call even if no clients were created.
    Uses function-level imports to avoid circular import issues.

    NOTE: Some modules build their own engines (compliance/gdpr, workflow managers).
    This cleanup only handles the centralized registry - those are not covered.

    Example:
        >>> from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients
        >>> await cleanup_all_clients()  # Call in FastAPI lifespan shutdown
    """
    logger.info("Starting application client cleanup...")

    # 1. Close CacheService Redis clients FIRST (fastest, least dependencies)
    try:
        from mcp_server_langgraph.core.cache import get_cache

        cache = get_cache()
        if cache:
            # Close both sync and async Redis clients
            cache.close()  # Sync Redis client
            await cache.aclose()  # Async Redis client (idempotent - safe if already closed)
            logger.info("CacheService Redis clients closed")
    except Exception as e:
        logger.warning(f"Error closing CacheService: {e}")

    # 2. Dispose PostgreSQL engine registry
    try:
        from mcp_server_langgraph.database.session import dispose_all_engines

        await dispose_all_engines()  # Safe if no engines created
        logger.info("PostgreSQL engine registry disposed")
    except Exception as e:
        logger.warning(f"Error disposing PostgreSQL engines: {e}")

    # 3. Close sync Qdrant client (SYNC - no await!)
    try:
        from mcp_server_langgraph.storage.vectors.factory import close_qdrant_client

        close_qdrant_client()  # Idempotent - safe if no client created
        logger.info("Sync Qdrant client closed")
    except Exception as e:
        logger.warning(f"Error closing sync Qdrant client: {e}")

    # 3b. Close async Qdrant client (ASYNC - requires await!)
    try:
        from mcp_server_langgraph.storage.vectors.factory import (
            aclose_async_qdrant_client,
        )

        await aclose_async_qdrant_client()  # Idempotent - safe if no client created
        logger.info("Async Qdrant client closed")
    except Exception as e:
        logger.warning(f"Error closing async Qdrant client: {e}")

    # 4. Close APIKeyManager Redis client
    try:
        from mcp_server_langgraph.core import dependencies as deps_module

        if deps_module._api_key_manager is not None:
            await deps_module._api_key_manager.aclose()
            deps_module._api_key_manager = None
            logger.info("APIKeyManager Redis client closed")
    except Exception as e:
        logger.warning(f"Error closing APIKeyManager: {e}")

    # 5. Close TokenDenylist Redis client
    try:
        from mcp_server_langgraph.core import dependencies as deps_module

        if deps_module._token_denylist is not None:
            await deps_module._token_denylist.aclose()
            deps_module._token_denylist = None
            logger.info("TokenDenylist Redis client closed")
    except Exception as e:
        logger.warning(f"Error closing TokenDenylist: {e}")

    # 6. Close ConversationStore Redis client (SYNC)
    try:
        from mcp_server_langgraph.core.storage import conversation_store as conv_module

        if conv_module._conversation_store is not None:
            conv_module._conversation_store.close()
            conv_module._conversation_store = None
            logger.info("ConversationStore Redis client closed")
    except Exception as e:
        logger.warning(f"Error closing ConversationStore: {e}")

    # 7. Close Session service Redis/PostgreSQL clients
    try:
        from mcp_server_langgraph.api.v1.sessions import cleanup_session_service

        await cleanup_session_service()  # Idempotent - safe if no clients created
        logger.info("Session service clients closed")
    except Exception as e:
        logger.warning(f"Error closing Session service: {e}")

    # 8. Close auth session store Redis client
    try:
        from mcp_server_langgraph.auth import session as session_module

        if session_module._session_store is not None:
            await session_module._session_store.aclose()
            session_module._session_store = None
            logger.info("Auth session store closed")
    except Exception as e:
        logger.warning(f"Error closing auth session store: {e}")

    logger.info("Application client cleanup complete")
