"""
Router registration module.

Centralizes router registration using the RouterRegistry pattern.
This enables OCP-compliant extensibility for adding new API routes.

Reference: Phase 2.3 OCP integration follow-up
"""

from mcp_server_langgraph.api.router_registry import RouterRegistry
from mcp_server_langgraph.core.config import settings


def register_default_routers(registry: RouterRegistry) -> None:
    """
    Register all default application routers.

    This function registers the core routers in the correct order:
    1. Health check (no auth required)
    2. API management routers
    3. Feature routers
    4. Unified v1 API

    Args:
        registry: RouterRegistry instance to register routers to
    """
    # Import routers here to avoid circular imports
    from mcp_server_langgraph.api import (
        api_keys_router,
        gdpr_router,
        health_router,
        scim_router,
        service_principals_router,
        studio_router,
    )
    from mcp_server_langgraph.api.metrics import router as metrics_router
    from mcp_server_langgraph.api.v1 import v1_router
    from mcp_server_langgraph.api.v1.notification_websocket import (
        router as notification_ws_router,
    )

    # Health check first (doesn't require auth)
    registry.register(health_router, tags=["health"])

    # API management routers
    registry.register(api_keys_router, tags=["api-keys"])
    registry.register(service_principals_router, tags=["service-principals"])

    # Compliance routers
    registry.register(gdpr_router, tags=["gdpr"])
    registry.register(scim_router, tags=["scim"])

    # Feature routers
    registry.register(studio_router, tags=["studio"])

    # Metrics routers (HEART framework)
    registry.register(metrics_router, tags=["metrics"])

    # Unified v1 API (BFF architecture)
    registry.register(v1_router, prefix="/api/v1", tags=["v1"])

    # Notification WebSocket (at /ws/notifications for frontend compatibility)
    registry.register(notification_ws_router, prefix="/ws", tags=["notifications"])

    # OAuth 2.0 Protected Resource Metadata (RFC 9728 / MCP 2025-11-25)
    # This enables OAuth clients to discover authorization servers
    from mcp_server_langgraph.mcp.protected_resource import (
        create_protected_resource_router,
        get_default_mcp_scopes,
    )

    # Build authorization server URL from Keycloak settings
    auth_server_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}"
    mcp_server_url = getattr(settings, "mcp_server_url", None) or "https://localhost"

    protected_resource_router = create_protected_resource_router(
        resource_url=mcp_server_url,
        authorization_servers=[auth_server_url],
        scopes_supported=get_default_mcp_scopes(),
    )
    registry.register(protected_resource_router, tags=["OAuth 2.0"])
