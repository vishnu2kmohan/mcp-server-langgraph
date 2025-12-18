"""
Security Bootstrap Module.

Initializes authentication and authorization components:
- AuthMiddleware for JWT validation
- OpenFGA client for fine-grained authorization
- User provider based on AUTH_PROVIDER setting
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING


logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from mcp_server_langgraph.auth.middleware import AuthMiddleware
    from mcp_server_langgraph.auth.openfga import OpenFGAClient
    from mcp_server_langgraph.auth.user_provider import UserProvider
    from mcp_server_langgraph.core.config import Settings


@dataclass
class SecurityState:
    """
    Security state after authentication/authorization initialization.

    Holds references to auth middleware and OpenFGA client.
    """

    auth_middleware: "AuthMiddleware | None" = None
    openfga_client: "OpenFGAClient | None" = None
    user_provider: "UserProvider | None" = None

    async def cleanup(self) -> None:
        """
        Cleanup security resources.

        Closes OpenFGA client to release aiohttp session.
        """
        if self.openfga_client is not None:
            try:
                await self.openfga_client.close()
            except Exception as e:
                logger.debug("Operation failed: %s", e)


async def init_auth(settings: "Settings") -> SecurityState:
    """
    Initialize authentication and authorization components.

    This includes:
    1. Creating user provider based on AUTH_PROVIDER setting
    2. Creating AuthMiddleware for JWT validation
    3. Initializing OpenFGA client (async) if configured

    Args:
        settings: Application settings

    Returns:
        SecurityState with initialized components

    Example:
        state = await init_auth(settings)
        app.add_middleware(AuthRequestMiddleware, auth_middleware=state.auth_middleware)
        app.state.openfga_client = state.openfga_client
    """
    from mcp_server_langgraph.auth.factory import create_user_provider
    from mcp_server_langgraph.auth.middleware import AuthMiddleware
    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig
    from mcp_server_langgraph.observability.telemetry import logger

    # Create user provider based on AUTH_PROVIDER setting
    user_provider = create_user_provider(settings)

    # Create auth middleware
    auth_middleware = AuthMiddleware(
        secret_key=settings.jwt_secret_key,
        settings=settings,
        user_provider=user_provider,
    )

    # Initialize OpenFGA client (async)
    openfga_client: OpenFGAClient | None = None
    try:
        has_store_config = settings.openfga_store_id or settings.openfga_store_name
        if has_store_config:
            # Construct OIDC issuer URL if not explicitly provided
            oidc_issuer = settings.openfga_oidc_issuer
            if not oidc_issuer and settings.openfga_oidc_client_id and settings.openfga_oidc_client_secret:
                oidc_issuer = f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"

            openfga_config = OpenFGAConfig(
                api_url=settings.openfga_api_url,
                store_id=settings.openfga_store_id,
                store_name=settings.openfga_store_name,
                model_id=settings.openfga_model_id,
                oidc_client_id=settings.openfga_oidc_client_id,
                oidc_client_secret=settings.openfga_oidc_client_secret,
                oidc_issuer=oidc_issuer,
                preshared_key=settings.openfga_preshared_key,
            )
            openfga_client = OpenFGAClient(config=openfga_config)
            # Async initialization
            await openfga_client._ensure_initialized()
            logger.info(
                "OpenFGA client initialized",
                extra={
                    "store_id": openfga_client.store_id,
                    "model_id": openfga_client.model_id,
                },
            )
        else:
            logger.warning(
                "OpenFGA not configured - authorization will be degraded. "
                "Set OPENFGA_STORE_ID or OPENFGA_STORE_NAME to enable."
            )
    except Exception as e:
        logger.warning(f"Failed to initialize OpenFGA client: {e}")
        openfga_client = None

    return SecurityState(
        auth_middleware=auth_middleware,
        openfga_client=openfga_client,
        user_provider=user_provider,
    )
