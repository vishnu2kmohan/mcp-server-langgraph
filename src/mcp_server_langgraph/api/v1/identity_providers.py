"""
Identity Provider Discovery API

Provides endpoint to discover available SSO identity providers
configured in Keycloak for the login page.

Supports:
- Social logins (Google, GitHub, Facebook, etc.)
- Enterprise SSO (OIDC, SAML providers)
- Identity provider hints for direct SSO login

Reference: https://www.keycloak.org/docs/latest/server_admin/#identity_broker
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(
    prefix="/identity-providers",
    tags=["Identity Providers"],
)

# =============================================================================
# Response Models
# =============================================================================


class IdentityProviderResponse(BaseModel):
    """Single identity provider for login page display."""

    alias: str = Field(description="Unique identifier for the IdP (used in kc_idp_hint)")
    display_name: str = Field(description="Human-readable name for display")
    provider_type: str = Field(description="Type: 'social' or 'enterprise'")
    provider_id: str = Field(description="Keycloak provider type (google, oidc, saml, etc.)")
    icon: str = Field(description="Icon name for UI display")
    login_url: str = Field(description="URL to initiate SSO login with this provider")


class IdentityProvidersListResponse(BaseModel):
    """Response containing all available identity providers."""

    identity_providers: list[IdentityProviderResponse] = Field(
        default_factory=list,
        description="Available identity providers for login",
    )
    has_social_login: bool = Field(
        default=False,
        description="Whether social login providers are available",
    )
    has_enterprise_sso: bool = Field(
        default=False,
        description="Whether enterprise SSO providers are available",
    )
    error: str | None = Field(
        default=None,
        description="Error message if IdP discovery failed",
    )


# =============================================================================
# Provider Type and Icon Mapping
# =============================================================================

# Social login providers
SOCIAL_PROVIDERS = {"google", "github", "facebook", "twitter", "linkedin", "apple", "instagram", "paypal", "stackoverflow"}

# Enterprise SSO providers
ENTERPRISE_PROVIDERS = {"oidc", "saml", "keycloak-oidc", "microsoft", "bitbucket"}

# Icon mapping for known providers
PROVIDER_ICONS = {
    "google": "google",
    "github": "github",
    "facebook": "facebook",
    "twitter": "twitter",
    "linkedin": "linkedin",
    "apple": "apple",
    "microsoft": "microsoft",
    "instagram": "instagram",
    "paypal": "paypal",
    "stackoverflow": "stackoverflow",
    "bitbucket": "bitbucket",
    "oidc": "key",
    "saml": "shield",
    "keycloak-oidc": "key",
}


def get_provider_type(provider_id: str) -> str:
    """Classify provider as social or enterprise."""
    if provider_id.lower() in SOCIAL_PROVIDERS:
        return "social"
    return "enterprise"


def get_provider_icon(provider_id: str) -> str:
    """Get icon name for a provider."""
    return PROVIDER_ICONS.get(provider_id.lower(), "external-link")


# =============================================================================
# Keycloak Admin API Integration
# =============================================================================

# Cache for identity providers (avoid repeated Keycloak calls)
_idp_cache: dict[str, Any] = {
    "providers": None,
    "expires_at": None,
}
_cache_lock = asyncio.Lock()
CACHE_TTL_SECONDS = 300  # 5 minutes


def clear_idp_cache() -> None:
    """Clear the identity provider cache. Used for testing."""
    global _idp_cache
    _idp_cache["providers"] = None
    _idp_cache["expires_at"] = None


async def get_keycloak_admin_token() -> str | None:
    """
    Get admin access token for Keycloak Admin API.

    Uses Resource Owner Password Credentials (ROPC) grant with admin credentials.
    This is consistent with how KeycloakUserProvider uses admin credentials.
    """
    # Check if admin credentials are configured
    if not settings.keycloak_admin_password:
        logger.debug("Keycloak admin password not configured, IdP discovery disabled")
        return None

    token_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_admin_realm}/protocol/openid-connect/token"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": settings.keycloak_admin_client_id,
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            token: str | None = response.json().get("access_token")
            return token
    except Exception as e:
        logger.warning(f"Failed to get Keycloak admin token: {e}")
        return None


async def fetch_keycloak_idps() -> list[dict[str, Any]]:
    """
    Fetch identity providers from Keycloak Admin API.

    Returns list of IdP configurations from the realm.
    """
    admin_token = await get_keycloak_admin_token()
    if not admin_token:
        logger.warning("No admin token available, cannot fetch IdPs")
        return []

    idp_url = f"{settings.keycloak_server_url}/admin/realms/{settings.keycloak_realm}/identity-provider/instances"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                idp_url,
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            idps: list[dict[str, Any]] = response.json()
            return idps
    except Exception as e:
        logger.warning(f"Failed to fetch identity providers from Keycloak: {e}")
        return []


def build_login_url(idp_alias: str) -> str:
    """
    Build OAuth2 authorization URL with kc_idp_hint.

    This URL will redirect the user directly to the specified IdP.
    """
    # Base authorization URL
    auth_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/auth"

    # Build query parameters
    params = {
        "client_id": settings.keycloak_client_id,
        "redirect_uri": settings.oauth2_redirect_uri or f"{settings.frontend_url}/oauth2/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "kc_idp_hint": idp_alias,
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{auth_url}?{query_string}"


def process_idp_response(raw_idps: list[dict[str, Any]]) -> list[IdentityProviderResponse]:
    """
    Process raw Keycloak IdP data into response format.

    Filters disabled and hidden providers, maps icons and types.
    """
    result = []

    for idp in raw_idps:
        # Skip disabled providers
        if not idp.get("enabled", False):
            continue

        # Skip providers hidden on login page
        config = idp.get("config", {})
        if config.get("hideOnLoginPage", "false").lower() == "true":
            continue

        alias = idp.get("alias", "")
        provider_id = idp.get("providerId", "")
        display_name = idp.get("displayName") or alias.replace("-", " ").title()

        result.append(
            IdentityProviderResponse(
                alias=alias,
                display_name=display_name,
                provider_type=get_provider_type(provider_id),
                provider_id=provider_id,
                icon=get_provider_icon(provider_id),
                login_url=build_login_url(alias),
            )
        )

    return result


# =============================================================================
# API Endpoint
# =============================================================================


async def get_identity_providers() -> IdentityProvidersListResponse:
    """
    Get available identity providers for login page.

    Uses caching to avoid repeated Keycloak Admin API calls.
    """
    global _idp_cache

    # Check cache
    async with _cache_lock:
        if _idp_cache["providers"] is not None and _idp_cache["expires_at"] and datetime.now(UTC) < _idp_cache["expires_at"]:
            cached: IdentityProvidersListResponse = _idp_cache["providers"]
            return cached

    # Fetch from Keycloak
    try:
        raw_idps = await fetch_keycloak_idps()
        providers = process_idp_response(raw_idps)

        # Classify providers
        has_social = any(p.provider_type == "social" for p in providers)
        has_enterprise = any(p.provider_type == "enterprise" for p in providers)

        response = IdentityProvidersListResponse(
            identity_providers=providers,
            has_social_login=has_social,
            has_enterprise_sso=has_enterprise,
        )

        # Update cache
        async with _cache_lock:
            _idp_cache["providers"] = response
            _idp_cache["expires_at"] = datetime.now(UTC) + timedelta(seconds=CACHE_TTL_SECONDS)

        return response

    except Exception as e:
        logger.error(f"Error fetching identity providers: {e}")
        return IdentityProvidersListResponse(
            identity_providers=[],
            has_social_login=False,
            has_enterprise_sso=False,
            error="Unable to fetch identity providers",
        )


@router.get("")
async def list_identity_providers() -> IdentityProvidersListResponse:
    """
    List available identity providers for SSO login.

    Returns all enabled identity providers configured in Keycloak,
    including social logins (Google, GitHub) and enterprise SSO (OIDC, SAML).

    Each provider includes a login_url with kc_idp_hint that can be used
    to initiate SSO directly with that provider.

    Example response:
    ```json
    {
        "identity_providers": [
            {
                "alias": "google",
                "display_name": "Google",
                "provider_type": "social",
                "provider_id": "google",
                "icon": "google",
                "login_url": "https://.../auth?...&kc_idp_hint=google"
            }
        ],
        "has_social_login": true,
        "has_enterprise_sso": false
    }
    ```
    """
    return await get_identity_providers()
