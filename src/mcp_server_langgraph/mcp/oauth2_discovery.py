"""
OAuth2 Discovery Service for MCP 2025-11-25 Compliance

Implements:
- Authorization Server Metadata Discovery (RFC 8414)
- OpenID Connect Discovery fallback
- Protected Resource Metadata (RFC 9728)
- Client ID Metadata Documents (SEP-991)
- PKCE verification
- Resource Parameter (RFC 8707)

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse

from pydantic import BaseModel, Field


class HTTPClient(Protocol):
    """Protocol for async HTTP client."""

    async def get(self, url: str, timeout: int = 30) -> Any:
        """Make GET request."""
        ...


class OAuth2DiscoveryError(Exception):
    """Base error for OAuth2 discovery failures."""

    pass


class PKCENotSupportedError(OAuth2DiscoveryError):
    """Error when PKCE is not supported by authorization server."""

    pass


class AuthorizationServerMetadata(BaseModel):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""

    issuer: str = Field(description="Authorization server's issuer identifier")
    authorization_endpoint: str = Field(description="URL of authorization endpoint")
    token_endpoint: str = Field(description="URL of token endpoint")
    code_challenge_methods_supported: list[str] = Field(
        default_factory=list,
        description="PKCE code challenge methods supported",
    )
    # Optional fields
    registration_endpoint: str | None = Field(
        default=None,
        description="URL of dynamic client registration endpoint",
    )
    scopes_supported: list[str] | None = Field(
        default=None,
        description="Scopes supported by authorization server",
    )
    response_types_supported: list[str] | None = Field(
        default=None,
        description="Response types supported",
    )
    grant_types_supported: list[str] | None = Field(
        default=None,
        description="Grant types supported",
    )
    token_endpoint_auth_methods_supported: list[str] | None = Field(
        default=None,
        description="Client authentication methods for token endpoint",
    )
    client_id_metadata_document_supported: bool = Field(
        default=False,
        description="Whether client ID metadata documents are supported (SEP-991)",
    )
    jwks_uri: str | None = Field(
        default=None,
        description="URL of JSON Web Key Set",
    )


class ProtectedResourceMetadata(BaseModel):
    """OAuth 2.0 Protected Resource Metadata (RFC 9728)."""

    resource: str = Field(description="Protected resource identifier")
    authorization_servers: list[str] = Field(
        description="Authorization servers for this resource",
    )
    scopes_supported: list[str] = Field(
        default_factory=list,
        description="Scopes supported by this resource",
    )
    bearer_methods_supported: list[str] = Field(
        default_factory=lambda: ["header"],
        description="Methods for sending bearer tokens",
    )


class ClientMetadataDocument(BaseModel):
    """Client ID Metadata Document (SEP-991)."""

    client_id: str = Field(description="Client ID (must match document URL)")
    client_name: str = Field(description="Human-readable client name")
    redirect_uris: list[str] = Field(description="Registered redirect URIs")
    # Optional fields
    client_uri: str | None = Field(default=None, description="Client homepage URL")
    logo_uri: str | None = Field(default=None, description="Client logo URL")
    grant_types: list[str] = Field(
        default_factory=lambda: ["authorization_code"],
        description="Supported grant types",
    )
    response_types: list[str] = Field(
        default_factory=lambda: ["code"],
        description="Supported response types",
    )
    token_endpoint_auth_method: str = Field(
        default="none",
        description="Token endpoint authentication method",
    )
    scope: str | None = Field(default=None, description="Default scope")
    contacts: list[str] = Field(
        default_factory=list,
        description="Contact information",
    )
    tos_uri: str | None = Field(default=None, description="Terms of service URL")
    policy_uri: str | None = Field(default=None, description="Privacy policy URL")


class OAuth2DiscoveryService:
    """
    OAuth2 Discovery Service for MCP 2025-11-25 compliance.

    Implements all required OAuth 2.1 discovery mechanisms:
    - RFC 8414: Authorization Server Metadata
    - RFC 9728: Protected Resource Metadata
    - SEP-991: Client ID Metadata Documents
    - RFC 8707: Resource Indicators
    """

    def __init__(
        self,
        http_client: HTTPClient,
        cache_ttl: int = 3600,
    ) -> None:
        """
        Initialize OAuth2 discovery service.

        Args:
            http_client: Async HTTP client for fetching metadata
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self._http_client = http_client
        self._cache_ttl = cache_ttl
        # Caches: url -> (metadata, expiry)
        self._as_cache: dict[str, tuple[AuthorizationServerMetadata, datetime]] = {}
        self._prm_cache: dict[str, tuple[ProtectedResourceMetadata, datetime]] = {}
        self._client_cache: dict[str, tuple[ClientMetadataDocument, datetime]] = {}

    # =========================================================================
    # Authorization Server Metadata Discovery (RFC 8414)
    # =========================================================================

    async def discover_authorization_server(
        self,
        issuer_url: str,
    ) -> AuthorizationServerMetadata:
        """
        Discover authorization server metadata.

        Per MCP 2025-11-25, clients MUST:
        1. Try /.well-known/oauth-authorization-server first
        2. Fall back to /.well-known/openid-configuration
        3. Handle issuer URLs with path components
        4. Verify PKCE support (code_challenge_methods_supported includes S256)

        Args:
            issuer_url: Authorization server issuer URL

        Returns:
            AuthorizationServerMetadata

        Raises:
            PKCENotSupportedError: If PKCE/S256 not supported
            OAuth2DiscoveryError: If discovery fails
        """
        # Check cache
        if issuer_url in self._as_cache:
            metadata, expiry = self._as_cache[issuer_url]
            if datetime.now(UTC) < expiry:
                return metadata

        # Build well-known URLs based on issuer URL structure
        parsed = urlparse(issuer_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path.rstrip("/")

        # URLs to try in order (per MCP spec)
        urls_to_try: list[str] = []

        if path:
            # Issuer with path: try path-based well-known first
            urls_to_try = [
                f"{base_url}/.well-known/oauth-authorization-server{path}",
                f"{base_url}/.well-known/openid-configuration{path}",
                f"{issuer_url}/.well-known/openid-configuration",
            ]
        else:
            # Issuer without path
            urls_to_try = [
                f"{base_url}/.well-known/oauth-authorization-server",
                f"{base_url}/.well-known/openid-configuration",
            ]

        # Try each URL
        last_error: Exception | None = None
        for url in urls_to_try:
            try:
                response = await self._http_client.get(url, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    metadata = self._parse_as_metadata(data)

                    # Verify PKCE support (MUST per MCP spec)
                    self._verify_pkce_support(metadata)

                    # Cache and return
                    expiry = datetime.now(UTC) + timedelta(seconds=self._cache_ttl)
                    self._as_cache[issuer_url] = (metadata, expiry)
                    return metadata
            except PKCENotSupportedError:
                raise  # Don't catch PKCE errors
            except Exception as e:
                last_error = e
                continue

        # All URLs failed
        raise OAuth2DiscoveryError(
            f"Failed to discover authorization server metadata for {issuer_url}. "
            f"Tried: {urls_to_try}. Last error: {last_error}"
        )

    def _parse_as_metadata(self, data: dict[str, Any]) -> AuthorizationServerMetadata:
        """Parse authorization server metadata from JSON."""
        return AuthorizationServerMetadata(
            issuer=data.get("issuer", ""),
            authorization_endpoint=data.get("authorization_endpoint", ""),
            token_endpoint=data.get("token_endpoint", ""),
            code_challenge_methods_supported=data.get("code_challenge_methods_supported", []),
            registration_endpoint=data.get("registration_endpoint"),
            scopes_supported=data.get("scopes_supported"),
            response_types_supported=data.get("response_types_supported"),
            grant_types_supported=data.get("grant_types_supported"),
            token_endpoint_auth_methods_supported=data.get("token_endpoint_auth_methods_supported"),
            client_id_metadata_document_supported=data.get("client_id_metadata_document_supported", False),
            jwks_uri=data.get("jwks_uri"),
        )

    def _verify_pkce_support(self, metadata: AuthorizationServerMetadata) -> None:
        """
        Verify PKCE support per MCP spec.

        Per MCP 2025-11-25:
        - Clients MUST verify code_challenge_methods_supported is present
        - Clients MUST refuse to proceed if absent
        - S256 MUST be in the list
        """
        if not metadata.code_challenge_methods_supported:
            raise PKCENotSupportedError(
                "Authorization server does not support PKCE. "
                "'code_challenge_methods_supported' is missing from metadata. "
                "MCP requires PKCE support per OAuth 2.1."
            )

        if "S256" not in metadata.code_challenge_methods_supported:
            raise PKCENotSupportedError(
                f"Authorization server does not support S256 PKCE method. "
                f"Supported methods: {metadata.code_challenge_methods_supported}. "
                f"MCP requires S256 per OAuth 2.1."
            )

    # =========================================================================
    # Protected Resource Metadata (RFC 9728)
    # =========================================================================

    async def discover_protected_resource(
        self,
        resource_url: str,
    ) -> ProtectedResourceMetadata:
        """
        Discover protected resource metadata.

        Per RFC 9728 and MCP 2025-11-25:
        1. Try /.well-known/oauth-protected-resource at path
        2. Fall back to domain root

        Args:
            resource_url: Resource URL (e.g., https://mcp.example.com/api)

        Returns:
            ProtectedResourceMetadata
        """
        # Check cache
        if resource_url in self._prm_cache:
            metadata, expiry = self._prm_cache[resource_url]
            if datetime.now(UTC) < expiry:
                return metadata

        # Build well-known URLs
        parsed = urlparse(resource_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path.rstrip("/")

        urls_to_try: list[str] = []
        if path:
            # Resource with path: try path-based first
            urls_to_try = [
                f"{base_url}/.well-known/oauth-protected-resource{path}",
                f"{base_url}/.well-known/oauth-protected-resource",
            ]
        else:
            urls_to_try = [
                f"{base_url}/.well-known/oauth-protected-resource",
            ]

        # Try each URL
        last_error: Exception | None = None
        for url in urls_to_try:
            try:
                response = await self._http_client.get(url, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    metadata = ProtectedResourceMetadata(
                        resource=data.get("resource", resource_url),
                        authorization_servers=data.get("authorization_servers", []),
                        scopes_supported=data.get("scopes_supported", []),
                        bearer_methods_supported=data.get("bearer_methods_supported", ["header"]),
                    )

                    # Cache and return
                    expiry = datetime.now(UTC) + timedelta(seconds=self._cache_ttl)
                    self._prm_cache[resource_url] = (metadata, expiry)
                    return metadata
            except Exception as e:
                last_error = e
                continue

        raise OAuth2DiscoveryError(
            f"Failed to discover protected resource metadata for {resource_url}. "
            f"Tried: {urls_to_try}. Last error: {last_error}"
        )

    def parse_www_authenticate(self, header: str) -> dict[str, str]:
        """
        Parse WWW-Authenticate header per MCP 2025-11-25.

        Expected format:
        Bearer resource_metadata="...", scope="...", error="..."

        Args:
            header: WWW-Authenticate header value

        Returns:
            Dict with parsed parameters
        """
        # Remove "Bearer " prefix
        if header.lower().startswith("bearer "):
            header = header[7:]

        # Parse key="value" pairs
        # Handle both quoted and unquoted values
        pattern = r'(\w+)="([^"]*)"'
        matches = re.findall(pattern, header)

        return dict(matches)

    # =========================================================================
    # Client ID Metadata Documents (SEP-991)
    # =========================================================================

    async def fetch_client_metadata(
        self,
        client_id: str,
    ) -> ClientMetadataDocument:
        """
        Fetch and validate client metadata document.

        Per SEP-991:
        - client_id must be HTTPS URL with path component
        - Fetched document's client_id must match URL exactly
        - Cache respecting HTTP cache headers

        Args:
            client_id: URL-formatted client ID

        Returns:
            ClientMetadataDocument

        Raises:
            OAuth2DiscoveryError: If fetch fails or validation fails
        """
        if not self.is_url_client_id(client_id):
            raise OAuth2DiscoveryError(
                f"Client ID '{client_id}' is not a valid URL-formatted client ID. Must be HTTPS URL with path component."
            )

        # Check cache
        if client_id in self._client_cache:
            metadata, expiry = self._client_cache[client_id]
            if datetime.now(UTC) < expiry:
                return metadata

        # Fetch metadata document
        try:
            response = await self._http_client.get(client_id, timeout=30)
            if response.status_code != 200:
                raise OAuth2DiscoveryError(f"Failed to fetch client metadata from {client_id}: HTTP {response.status_code}")

            data = response.json()

            # Validate client_id matches URL
            document_client_id = data.get("client_id", "")
            if document_client_id != client_id:
                raise OAuth2DiscoveryError(
                    f"Client ID mismatch: URL is '{client_id}' but document contains client_id='{document_client_id}'"
                )

            metadata = ClientMetadataDocument(
                client_id=data["client_id"],
                client_name=data.get("client_name", "Unknown Client"),
                redirect_uris=data.get("redirect_uris", []),
                client_uri=data.get("client_uri"),
                logo_uri=data.get("logo_uri"),
                grant_types=data.get("grant_types", ["authorization_code"]),
                response_types=data.get("response_types", ["code"]),
                token_endpoint_auth_method=data.get("token_endpoint_auth_method", "none"),
                scope=data.get("scope"),
                contacts=data.get("contacts", []),
                tos_uri=data.get("tos_uri"),
                policy_uri=data.get("policy_uri"),
            )

            # Cache
            expiry = datetime.now(UTC) + timedelta(seconds=self._cache_ttl)
            self._client_cache[client_id] = (metadata, expiry)
            return metadata

        except OAuth2DiscoveryError:
            raise
        except Exception as e:
            raise OAuth2DiscoveryError(f"Failed to fetch client metadata from {client_id}: {e}") from e

    def is_url_client_id(self, client_id: str) -> bool:
        """
        Check if client_id is URL-formatted per SEP-991.

        Requirements:
        - Must be HTTPS URL
        - Must have path component (not just domain)

        Args:
            client_id: Client ID to check

        Returns:
            True if valid URL-formatted client ID
        """
        try:
            parsed = urlparse(client_id)

            # Must be HTTPS
            if parsed.scheme != "https":
                return False

            # Must have netloc (domain)
            if not parsed.netloc:
                return False

            # Must have path component (not just "/" or empty)
            path = parsed.path.rstrip("/")
            return bool(path)
        except Exception:
            return False

    def validate_redirect_uri(
        self,
        redirect_uri: str,
        metadata: ClientMetadataDocument,
    ) -> bool:
        """
        Validate redirect URI against client metadata.

        Args:
            redirect_uri: Redirect URI to validate
            metadata: Client metadata document

        Returns:
            True if redirect URI is in metadata's redirect_uris
        """
        return redirect_uri in metadata.redirect_uris

    # =========================================================================
    # Resource Parameter (RFC 8707)
    # =========================================================================

    def build_authorization_url(
        self,
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        resource: str,
        state: str,
        code_challenge: str,
        scope: str | None = None,
    ) -> str:
        """
        Build authorization URL with resource parameter per RFC 8707.

        Args:
            authorization_endpoint: Authorization endpoint URL
            client_id: Client ID
            redirect_uri: Redirect URI
            resource: Resource indicator (e.g., https://mcp.example.com)
            state: State parameter
            code_challenge: PKCE code challenge
            scope: Optional scope

        Returns:
            Complete authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "resource": resource,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if scope:
            params["scope"] = scope

        return f"{authorization_endpoint}?{urlencode(params)}"

    def build_token_request_params(
        self,
        grant_type: str,
        code: str,
        redirect_uri: str,
        resource: str,
        code_verifier: str,
        client_id: str,
    ) -> dict[str, str]:
        """
        Build token request parameters with resource per RFC 8707.

        Args:
            grant_type: Grant type (authorization_code)
            code: Authorization code
            redirect_uri: Redirect URI
            resource: Resource indicator
            code_verifier: PKCE code verifier
            client_id: Client ID

        Returns:
            Dict of token request parameters
        """
        return {
            "grant_type": grant_type,
            "code": code,
            "redirect_uri": redirect_uri,
            "resource": resource,
            "code_verifier": code_verifier,
            "client_id": client_id,
        }

    # =========================================================================
    # WWW-Authenticate Header Building
    # =========================================================================

    def build_www_authenticate_header(
        self,
        resource_metadata: str,
        scope: str | None = None,
        error: str | None = None,
    ) -> str:
        """
        Build WWW-Authenticate header per MCP 2025-11-25.

        For 401 responses:
        Bearer resource_metadata="...", scope="..."

        For 403 responses:
        Bearer error="insufficient_scope", scope="...", resource_metadata="..."

        Args:
            resource_metadata: URL to protected resource metadata
            scope: Required scope(s)
            error: Error code (e.g., "insufficient_scope")

        Returns:
            WWW-Authenticate header value
        """
        parts: list[str] = []

        if error:
            parts.append(f'error="{error}"')

        if scope:
            parts.append(f'scope="{scope}"')

        parts.append(f'resource_metadata="{resource_metadata}"')

        return "Bearer " + ", ".join(parts)
