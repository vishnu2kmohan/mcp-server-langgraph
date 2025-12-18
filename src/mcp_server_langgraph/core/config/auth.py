"""
Authentication Configuration Module.

Settings for JWT, DPoP, Keycloak SSO, and OpenFGA authorization.
"""

from pydantic_settings import SettingsConfigDict

from mcp_server_langgraph.core.config.base import DomainSettings


class AuthSettings(DomainSettings):
    """
    Authentication and authorization settings.

    Covers:
    - JWT token configuration
    - DPoP (RFC 9449) proof-of-possession
    - Keycloak SSO integration
    - OpenFGA fine-grained authorization
    - OAuth2/PKCE configuration
    """

    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix, use standard env vars
        extra="ignore",
    )

    # JWT Configuration
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600
    use_password_hashing: bool = True

    # DPoP (Demonstrating Proof of Possession) - RFC 9449
    dpop_required: bool = False

    # Authorization Fallback Control
    # SECURITY: Controls whether authorization can fall back when OpenFGA is unavailable
    allow_auth_fallback: bool = False

    # Authentication Provider
    auth_provider: str = "inmemory"  # "inmemory", "keycloak"
    auth_mode: str = "token"  # "token" (JWT), "session"

    # Mock Authorization (Development)
    # SECURITY: Disabled by default in production
    enable_mock_authorization: bool | None = None

    # Keycloak Settings
    keycloak_server_url: str = "http://localhost:8082"
    keycloak_public_url: str | None = None
    keycloak_realm: str = "langgraph-agent"
    keycloak_client_id: str = "langgraph-client"
    keycloak_client_secret: str | None = None
    keycloak_admin_realm: str = "master"
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str | None = None
    keycloak_admin_client_id: str = "admin-cli"
    keycloak_admin_client_secret: str | None = None
    keycloak_verify_ssl: bool = True
    keycloak_timeout: int = 30

    # OpenFGA Configuration
    openfga_api_url: str = "http://localhost:8080"
    openfga_store_id: str | None = None
    openfga_store_name: str | None = None
    openfga_model_id: str | None = None
    openfga_oidc_client_id: str | None = None
    openfga_oidc_client_secret: str | None = None
    openfga_oidc_issuer: str | None = None
    openfga_preshared_key: str | None = None  # Legacy, use OIDC instead

    # Frontend URL for OAuth2 callbacks
    frontend_url: str = "http://localhost:5173"

    # OAuth2 Configuration
    oauth2_redirect_uri: str = "http://localhost:5173/studio/oauth/callback"
    oauth2_auth_callback_uri: str | None = None

    def get_mock_authorization_enabled(self, environment: str = "development") -> bool:
        """
        Get the effective value of enable_mock_authorization based on environment.

        SECURITY: Mock authorization is disabled by default in production.
        In development, it's enabled by default for better developer experience.

        Args:
            environment: Current environment (development, production, etc.)

        Returns:
            bool: True if mock authorization should be enabled
        """
        if self.enable_mock_authorization is not None:
            return self.enable_mock_authorization
        return environment == "development"


__all__ = ["AuthSettings"]
