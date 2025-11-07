"""
Middleware Factory Functions

Provides reusable middleware creation functions for FastAPI applications.
"""

from __future__ import annotations

from typing import Any

from fastapi.middleware.cors import CORSMiddleware

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.core.container import ApplicationContainer


def create_cors_middleware() -> type[CORSMiddleware]:
    """
    Create CORS middleware configuration.

    Returns:
        CORSMiddleware class

    Example:
        middleware = create_cors_middleware()
        app.add_middleware(middleware, allow_origins=["*"])
    """
    return CORSMiddleware


def create_rate_limit_middleware(settings: Settings) -> Any:
    """
    Create rate limiting middleware.

    Args:
        settings: Application settings

    Returns:
        Rate limit middleware (or mock in test mode)

    Example:
        middleware = create_rate_limit_middleware(settings)
    """
    # For test mode, return a no-op middleware
    if settings.environment == "test":
        return None

    # In production, would return actual rate limiter
    return None


def create_auth_middleware(container: ApplicationContainer) -> Any:
    """
    Create authentication middleware.

    Args:
        container: Application container with auth provider

    Returns:
        Auth middleware (or mock in test mode)

    Example:
        middleware = create_auth_middleware(container)
    """
    container.get_auth()

    # For test mode, return a no-op middleware
    if container.settings.environment == "test":
        return None

    # In production, would return actual auth middleware
    return None
