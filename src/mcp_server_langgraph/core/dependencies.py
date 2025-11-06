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
from mcp_server_langgraph.core.config import settings

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
                import redis.asyncio as redis

                # Build Redis URL with correct database number
                redis_url_with_db = f"{settings.redis_url}/{settings.api_key_cache_db}"

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
