"""
Authentication middleware factory for configurable auth providers

Centralizes AuthMiddleware creation based on settings configuration.
Supports multiple authentication backends:
- InMemoryUserProvider (development/testing)
- KeycloakUserProvider (production)
- Custom providers (extensibility)
"""

from typing import Optional

from mcp_server_langgraph.auth.keycloak import KeycloakConfig
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.session import RedisSessionStore, SessionStore
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider, KeycloakUserProvider, UserProvider
from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.observability.telemetry import logger


def create_user_provider(settings: Settings, openfga_client: Optional[OpenFGAClient] = None) -> UserProvider:
    """
    Create UserProvider based on settings configuration (production use)

    This is the recommended factory function for production code.
    It reads from the Settings object to automatically configure the provider.

    For test code, use `mcp_server_langgraph.auth.user_provider.create_user_provider()`
    which allows explicit provider_type and config specification.

    Args:
        settings: Application settings instance
        openfga_client: Optional OpenFGA client for role synchronization

    Returns:
        Configured UserProvider instance

    Raises:
        ValueError: If provider type is unknown or required config is missing

    See Also:
        mcp_server_langgraph.auth.user_provider.create_user_provider: Alternative factory for tests
    """
    provider_type = settings.auth_provider.lower()

    if provider_type == "inmemory":
        # SECURITY: Block InMemoryUserProvider in production/staging environments
        # Get environment with safe fallback to 'development'
        environment = getattr(settings, "environment", "development").lower()

        # Block in production and staging (allow in development/test)
        if environment in ("production", "staging", "prod", "stg"):
            raise RuntimeError(
                f"SECURITY: InMemoryUserProvider is not allowed in production environments. "
                f"Current environment: '{environment}'. "
                f"InMemoryUserProvider contains hardcoded demo credentials (alice:alice123, bob:bob123, admin:admin123) "
                f"and is only suitable for development/testing. "
                f"For production, use AUTH_PROVIDER=keycloak with proper SSO integration."
            )

        logger.info("Creating InMemoryUserProvider for authentication")
        logger.warning(
            f"InMemoryUserProvider is being used in '{environment}' environment. "
            f"This provider has hardcoded credentials and should NEVER be used in production."
        )

        # Validate JWT secret is configured
        if not settings.jwt_secret_key:
            raise ValueError(
                "CRITICAL: JWT secret key required for InMemoryUserProvider. " "Set JWT_SECRET_KEY environment variable."
            )

        return InMemoryUserProvider(secret_key=settings.jwt_secret_key, use_password_hashing=settings.use_password_hashing)

    elif provider_type == "keycloak":
        logger.info("Creating KeycloakUserProvider for authentication")

        # Validate Keycloak configuration
        if not settings.keycloak_client_secret:
            raise ValueError("CRITICAL: Keycloak client secret required. " "Set KEYCLOAK_CLIENT_SECRET environment variable.")

        # Build Keycloak configuration from settings
        keycloak_config = KeycloakConfig(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            admin_username=settings.keycloak_admin_username,
            admin_password=settings.keycloak_admin_password,
            verify_ssl=settings.keycloak_verify_ssl,
            timeout=settings.keycloak_timeout,
        )

        return KeycloakUserProvider(
            config=keycloak_config,
            openfga_client=openfga_client,
            sync_on_login=True,  # Auto-sync roles to OpenFGA on login
        )

    else:
        raise ValueError(
            f"Unknown auth provider: '{provider_type}'. "
            f"Supported providers: 'inmemory', 'keycloak'. "
            f"To add custom providers, extend UserProvider and update this factory."
        )


def create_session_store(settings: Settings) -> Optional[SessionStore]:
    """
    Create SessionStore based on settings configuration

    Args:
        settings: Application settings instance

    Returns:
        Configured SessionStore instance or None if sessions disabled
    """
    if settings.auth_mode != "session":
        # Token-based auth doesn't need session store
        logger.info("Session store not needed for token-based auth")
        return None

    backend = settings.session_backend.lower()

    if backend == "memory":
        logger.warning(
            "Using in-memory session store. Sessions will not persist across restarts. " "For production, use 'redis' backend."
        )
        # In-memory sessions are handled by default SessionStore (not implemented yet)
        # For now, return None and sessions won't be used
        return None

    elif backend == "redis":
        logger.info("Creating Redis session store")

        # Validate Redis configuration
        if not settings.redis_url:
            raise ValueError("CRITICAL: Redis URL required for Redis session store. " "Set REDIS_URL environment variable.")

        return RedisSessionStore(  # type: ignore[call-arg]
            redis_url=settings.redis_url,
            password=settings.redis_password,
            ssl=settings.redis_ssl,
            ttl_seconds=settings.session_ttl_seconds,
            sliding_window=settings.session_sliding_window,
            max_concurrent_sessions=settings.session_max_concurrent,
        )

    else:
        raise ValueError(f"Unknown session backend: '{backend}'. " f"Supported backends: 'memory', 'redis'.")


def create_auth_middleware(settings: Settings, openfga_client: Optional[OpenFGAClient] = None) -> AuthMiddleware:
    """
    Create AuthMiddleware with configured providers

    This factory reads settings and wires up the appropriate:
    - UserProvider (InMemory, Keycloak, custom)
    - SessionStore (Memory, Redis)
    - OpenFGA client (for fine-grained authorization)

    Args:
        settings: Application settings instance
        openfga_client: Optional OpenFGA client for authorization

    Returns:
        Fully configured AuthMiddleware instance

    Example:
        >>> from mcp_server_langgraph.core.config import settings
        >>> from mcp_server_langgraph.auth.openfga import OpenFGAClient
        >>> openfga = OpenFGAClient(...)
        >>> auth = create_auth_middleware(settings, openfga)
        >>> # Now auth uses the configured provider (InMemory or Keycloak)
    """
    # Create user provider based on settings
    user_provider = create_user_provider(settings, openfga_client)

    # Create session store if using session-based auth
    session_store = create_session_store(settings)

    # Build AuthMiddleware with all components
    auth = AuthMiddleware(
        secret_key=settings.jwt_secret_key,
        openfga_client=openfga_client,
        user_provider=user_provider,
        session_store=session_store,
    )

    logger.info(
        "AuthMiddleware created",
        extra={
            "auth_provider": settings.auth_provider,
            "auth_mode": settings.auth_mode,
            "session_backend": settings.session_backend if settings.auth_mode == "session" else "N/A",
            "openfga_enabled": openfga_client is not None,
        },
    )

    return auth
