"""
FastAPI Dependencies

Provides dependency injection for commonly used services.
"""

from typing import Any, Optional

from fastapi import Depends

from mcp_server_langgraph.auth.api_keys import APIKeyManager
from mcp_server_langgraph.auth.keycloak import KeycloakClient
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.service_principal import ServicePrincipalManager
from mcp_server_langgraph.core.config import Settings, settings

# Singleton instances (will be initialized on first use)
_keycloak_client: Optional[KeycloakClient] = None
_openfga_client: Optional[OpenFGAClient] = None
_service_principal_manager: Optional[ServicePrincipalManager] = None
_api_key_manager: Optional[APIKeyManager] = None


def get_keycloak_client() -> KeycloakClient:
    """Get Keycloak client instance (singleton)"""
    global _keycloak_client

    if _keycloak_client is None:
        from mcp_server_langgraph.auth.keycloak import KeycloakConfig

        keycloak_config = KeycloakConfig(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            admin_username=settings.keycloak_admin_username,
            admin_password=settings.keycloak_admin_password,
        )
        _keycloak_client = KeycloakClient(config=keycloak_config)

    return _keycloak_client


def get_openfga_client() -> Optional[OpenFGAClient]:
    """
    Get OpenFGA client instance (singleton)

    Returns None if OpenFGA is not fully configured (store_id or model_id missing).
    This allows graceful degradation when OpenFGA is intentionally disabled.
    """
    global _openfga_client

    if _openfga_client is None:
        from mcp_server_langgraph.auth.openfga import OpenFGAConfig
        from mcp_server_langgraph.observability.telemetry import logger

        # Validate that required configuration is present
        if not settings.openfga_store_id or not settings.openfga_model_id:
            logger.warning(
                "OpenFGA configuration incomplete - authorization will be degraded. "
                f"store_id: {settings.openfga_store_id}, model_id: {settings.openfga_model_id}. "
                "Set OPENFGA_STORE_ID and OPENFGA_MODEL_ID environment variables to enable OpenFGA."
            )
            return None

        openfga_config = OpenFGAConfig(
            api_url=settings.openfga_api_url,
            store_id=settings.openfga_store_id,
            model_id=settings.openfga_model_id,
        )
        _openfga_client = OpenFGAClient(config=openfga_config)

    return _openfga_client


def validate_production_auth_config(settings_obj: Settings) -> None:
    """
    Validate that production deployments have proper authorization configured.

    SECURITY: This function prevents production deployments from running with degraded
    authorization when OpenFGA is not configured and fallback is disabled.

    Implements remediation for OpenAI Codex Finding #1: Authorization Degradation

    Args:
        settings_obj: Settings object to validate

    Raises:
        RuntimeError: If production environment lacks required authorization infrastructure

    References:
        - tests/security/test_authorization_fallback_controls.py
        - CWE-862: Missing Authorization
    """
    if settings_obj.environment != "production":
        # Only enforce for production environment
        return

    # Check if OpenFGA is configured
    openfga_configured = bool(settings_obj.openfga_store_id and settings_obj.openfga_model_id)

    # Check if fallback is allowed
    allow_fallback = getattr(settings_obj, "allow_auth_fallback", False)

    # Production MUST have either:
    # 1. OpenFGA properly configured, OR
    # 2. Fallback explicitly disabled (fail-closed)
    if not openfga_configured and not allow_fallback:
        # This is the secure configuration - production with no OpenFGA will deny all auth requests
        # This is intentional fail-closed behavior
        from mcp_server_langgraph.observability.telemetry import logger

        logger.warning(
            "Production deployment without OpenFGA will deny all authorization requests. "
            "This is secure fail-closed behavior. Configure OpenFGA for production use.",
            extra={
                "environment": settings_obj.environment,
                "openfga_configured": openfga_configured,
                "allow_auth_fallback": allow_fallback,
            },
        )
        # This is actually a valid secure configuration, so we'll allow it
        # The authorization will just deny everything, which is secure
        return

    if not openfga_configured and allow_fallback:
        # SECURITY ERROR: Production with fallback enabled but no OpenFGA
        raise RuntimeError(
            "SECURITY ERROR: Production deployment requires OpenFGA authorization infrastructure. "
            f"OpenFGA is not configured (store_id: {settings_obj.openfga_store_id}, "
            f"model_id: {settings_obj.openfga_model_id}) but ALLOW_AUTH_FALLBACK=true. "
            "This configuration would allow degraded role-based authorization in production. "
            "Either: (1) Configure OpenFGA properly, or (2) Set ALLOW_AUTH_FALLBACK=false to fail-closed."
        )


def get_service_principal_manager(
    keycloak: KeycloakClient = Depends(get_keycloak_client),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> ServicePrincipalManager:
    """
    Get ServicePrincipalManager instance

    Args:
        keycloak: Keycloak client (injected)
        openfga: OpenFGA client (injected)

    Returns:
        ServicePrincipalManager instance
    """
    global _service_principal_manager

    if _service_principal_manager is None:
        _service_principal_manager = ServicePrincipalManager(
            keycloak_client=keycloak,
            openfga_client=openfga,
        )

    return _service_principal_manager


def get_api_key_manager(
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> APIKeyManager:
    """
    Get APIKeyManager instance with Redis caching if enabled

    Args:
        keycloak: Keycloak client (injected)

    Returns:
        APIKeyManager instance configured with Redis cache if settings.api_key_cache_enabled=True
    """
    global _api_key_manager

    if _api_key_manager is None:
        # Wire Redis client for API key caching if enabled (OpenAI Codex Finding #5)
        # IMPORTANT: This Redis client must be passed to APIKeyManager or caching will be disabled
        # Settings used:
        #   - api_key_cache_enabled: Enable/disable caching
        #   - api_key_cache_db: Redis database number (default: 2)
        #   - api_key_cache_ttl: Cache TTL in seconds (default: 3600)
        #   - redis_url: Redis connection URL
        #   - redis_password: Redis password (optional)
        #   - redis_ssl: Use SSL for Redis connection (default: False)
        redis_client: Optional[Any] = None
        if settings.api_key_cache_enabled and settings.redis_url:
            try:
                from urllib.parse import urlparse, urlunparse

                import redis.asyncio as redis

                # Build Redis URL with correct database number
                # Parse the URL to handle existing database numbers, trailing slashes, query params
                parsed = urlparse(settings.redis_url)

                # Remove existing database number from path (if present)
                # Redis URL path is typically empty or /db_number
                # We'll replace it with the configured database number
                new_path = f"/{settings.api_key_cache_db}"

                # Reconstruct URL with new database number
                redis_url_with_db = urlunparse(
                    (
                        parsed.scheme,  # redis:// or rediss://
                        parsed.netloc,  # host:port
                        new_path,  # /db_number
                        parsed.params,  # unused in Redis URLs
                        parsed.query,  # query parameters (if any)
                        parsed.fragment,  # fragment (if any)
                    )
                )

                # Create Redis client with configured credentials
                redis_client = redis.from_url(
                    redis_url_with_db,
                    password=settings.redis_password,
                    ssl=settings.redis_ssl,
                    decode_responses=True,
                )
            except ImportError:
                # Redis not installed, disable caching gracefully
                redis_client = None

        _api_key_manager = APIKeyManager(
            keycloak_client=keycloak,
            redis_client=redis_client,
            cache_ttl=settings.api_key_cache_ttl,
            cache_enabled=settings.api_key_cache_enabled,
        )

        # Validation: Ensure cache is actually enabled if requested (prevent regression)
        if settings.api_key_cache_enabled and settings.redis_url and not _api_key_manager.cache_enabled:
            raise RuntimeError(
                "API key caching configuration error! "
                f"settings.api_key_cache_enabled=True but APIKeyManager.cache_enabled=False. "
                f"Redis client: {redis_client}. "
                "This indicates Redis client was not properly wired."
            )

    return _api_key_manager


# ==============================================================================
# Testing Utilities (CODEX Finding #6)
# ==============================================================================


def reset_singleton_dependencies() -> None:
    """
    Reset all singleton dependencies to None.

    CODEX FINDING #6: Permanently skipped test due to singleton cache.
    This function enables proper testing of dependency wiring logic by
    allowing tests to reset singletons between test runs.

    Usage in tests:
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        def test_dependency_wiring():
            reset_singleton_dependencies()
            # Now test dependency initialization with mocked settings
            ...

    WARNING: This should ONLY be used in tests. Never call in production code.
    """
    global _keycloak_client, _openfga_client, _service_principal_manager, _api_key_manager

    _keycloak_client = None
    _openfga_client = None
    _service_principal_manager = None
    _api_key_manager = None
