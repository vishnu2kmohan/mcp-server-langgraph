"""
FastAPI Dependencies

Provides dependency injection for commonly used services.
"""

from typing import Optional

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
        )
        _keycloak_client = KeycloakClient(config=keycloak_config)

    return _keycloak_client


def get_openfga_client() -> OpenFGAClient:
    """Get OpenFGA client instance (singleton)"""
    global _openfga_client

    if _openfga_client is None:
        from mcp_server_langgraph.auth.openfga import OpenFGAConfig

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
    Get APIKeyManager instance

    Args:
        keycloak: Keycloak client (injected)

    Returns:
        APIKeyManager instance
    """
    global _api_key_manager

    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(keycloak_client=keycloak)

    return _api_key_manager
