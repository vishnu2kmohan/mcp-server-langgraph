"""
OAuth2 Discovery Service Unit Tests

TDD: Tests written FIRST for MCP 2025-11-25 OAuth2 discovery compliance.
Tests cover:
- Authorization Server Metadata Discovery (RFC 8414)
- OpenID Connect Discovery fallback
- Protected Resource Metadata (RFC 9728)
- Client ID Metadata Documents (SEP-991)
- PKCE verification
- Resource Parameter (RFC 8707)

NOTE: These tests are in TDD RED phase - the implementation module
doesn't exist yet. Tests are skipped until oauth2_discovery.py is created.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

# TDD RED phase: Skip entire module if implementation doesn't exist yet
# This allows the test file to exist for TDD workflow without breaking CI
pytest.importorskip(
    "mcp_server_langgraph.mcp.oauth2_discovery",
    reason="TDD RED phase: oauth2_discovery module not implemented yet",
)

from mcp_server_langgraph.mcp.oauth2_discovery import (
    ClientMetadataDocument,
    OAuth2DiscoveryError,
    OAuth2DiscoveryService,
    PKCENotSupportedError,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="oauth2_discovery"),
]


@pytest.mark.xdist_group(name="testoauth2discovery")
class TestOAuth2DiscoveryService:
    """TDD tests for OAuth2 discovery service per MCP 2025-11-25."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create a mock HTTP client."""
        client = AsyncMock()  # noqa: async-mock-config
        return client

    @pytest.fixture
    def discovery_service(self, mock_http_client: AsyncMock) -> OAuth2DiscoveryService:
        """Create discovery service with mocked HTTP client."""
        return OAuth2DiscoveryService(http_client=mock_http_client)

    # =========================================================================
    # Authorization Server Metadata Discovery Tests (RFC 8414)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_discover_authorization_server_from_oauth_metadata(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Discovers AS metadata from /.well-known/oauth-authorization-server."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": ["S256"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN
        metadata = await discovery_service.discover_authorization_server(issuer_url)

        # THEN
        assert metadata.issuer == "https://auth.example.com"
        assert metadata.authorization_endpoint == "https://auth.example.com/authorize"
        assert metadata.token_endpoint == "https://auth.example.com/token"
        assert "S256" in metadata.code_challenge_methods_supported
        mock_http_client.get.assert_called_once_with(
            "https://auth.example.com/.well-known/oauth-authorization-server",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_discover_authorization_server_falls_back_to_oidc(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Falls back to /.well-known/openid-configuration when OAuth fails."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        # First call (oauth) fails, second call (oidc) succeeds
        oauth_response = MagicMock()
        oauth_response.status_code = 404
        oidc_response = MagicMock()
        oidc_response.status_code = 200
        oidc_response.json.return_value = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": ["S256"],
        }
        mock_http_client.get.side_effect = [oauth_response, oidc_response]

        # WHEN
        metadata = await discovery_service.discover_authorization_server(issuer_url)

        # THEN
        assert metadata.issuer == "https://auth.example.com"
        assert mock_http_client.get.call_count == 2
        # Second call should be to openid-configuration
        mock_http_client.get.assert_called_with(
            "https://auth.example.com/.well-known/openid-configuration",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_discover_authorization_server_with_path_components(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Handles issuer URLs with path components (multi-tenant)."""
        # GIVEN
        issuer_url = "https://auth.example.com/tenant1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com/tenant1",
            "authorization_endpoint": "https://auth.example.com/tenant1/authorize",
            "token_endpoint": "https://auth.example.com/tenant1/token",
            "code_challenge_methods_supported": ["S256"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN
        metadata = await discovery_service.discover_authorization_server(issuer_url)

        # THEN
        assert metadata.issuer == "https://auth.example.com/tenant1"
        # Should try path-based well-known first
        mock_http_client.get.assert_called_once_with(
            "https://auth.example.com/.well-known/oauth-authorization-server/tenant1",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_discover_authorization_server_raises_on_no_pkce_support(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Raises error when PKCE is not supported."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            # No code_challenge_methods_supported!
        }
        mock_http_client.get.return_value = mock_response

        # WHEN/THEN
        with pytest.raises(PKCENotSupportedError) as exc_info:
            await discovery_service.discover_authorization_server(issuer_url)

        assert "PKCE" in str(exc_info.value)
        assert "code_challenge_methods_supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_discover_authorization_server_raises_on_missing_s256(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Raises error when S256 is not in supported methods."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": ["plain"],  # Only plain, no S256
        }
        mock_http_client.get.return_value = mock_response

        # WHEN/THEN
        with pytest.raises(PKCENotSupportedError) as exc_info:
            await discovery_service.discover_authorization_server(issuer_url)

        assert "S256" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_discover_authorization_server_raises_on_both_endpoints_fail(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Raises error when all discovery endpoints fail."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        # WHEN/THEN
        with pytest.raises(OAuth2DiscoveryError) as exc_info:
            await discovery_service.discover_authorization_server(issuer_url)

        assert "authorization server" in str(exc_info.value).lower()

    # =========================================================================
    # Protected Resource Metadata Tests (RFC 9728)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_discover_protected_resource_from_well_known(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Discovers protected resource metadata from well-known URI."""
        # GIVEN
        resource_url = "https://mcp.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": "https://mcp.example.com",
            "authorization_servers": ["https://auth.example.com"],
            "scopes_supported": ["files:read", "files:write"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN
        metadata = await discovery_service.discover_protected_resource(resource_url)

        # THEN
        assert metadata.resource == "https://mcp.example.com"
        assert "https://auth.example.com" in metadata.authorization_servers
        assert "files:read" in metadata.scopes_supported
        mock_http_client.get.assert_called_once_with(
            "https://mcp.example.com/.well-known/oauth-protected-resource",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_discover_protected_resource_with_path(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Discovers protected resource with path component."""
        # GIVEN
        resource_url = "https://mcp.example.com/public/mcp"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resource": "https://mcp.example.com/public/mcp",
            "authorization_servers": ["https://auth.example.com"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN
        metadata = await discovery_service.discover_protected_resource(resource_url)

        # THEN
        assert metadata.resource == "https://mcp.example.com/public/mcp"
        # Should try path-based well-known first
        mock_http_client.get.assert_called_once_with(
            "https://mcp.example.com/.well-known/oauth-protected-resource/public/mcp",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_parse_protected_resource_from_www_authenticate(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Parses protected resource metadata from WWW-Authenticate header."""
        # GIVEN
        www_authenticate = (
            'Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource", '
            'scope="files:read files:write"'
        )

        # WHEN
        result = discovery_service.parse_www_authenticate(www_authenticate)

        # THEN
        assert result["resource_metadata"] == "https://mcp.example.com/.well-known/oauth-protected-resource"
        assert result["scope"] == "files:read files:write"

    @pytest.mark.asyncio
    async def test_parse_www_authenticate_with_error(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Parses WWW-Authenticate with error and scope."""
        # GIVEN
        www_authenticate = (
            'Bearer error="insufficient_scope", '
            'scope="files:read files:write user:profile", '
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"'
        )

        # WHEN
        result = discovery_service.parse_www_authenticate(www_authenticate)

        # THEN
        assert result["error"] == "insufficient_scope"
        assert result["scope"] == "files:read files:write user:profile"
        assert result["resource_metadata"] == "https://mcp.example.com/.well-known/oauth-protected-resource"

    # =========================================================================
    # Client ID Metadata Documents Tests (SEP-991)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_fetch_client_metadata_document(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Fetches and validates client metadata document."""
        # GIVEN
        client_id = "https://app.example.com/oauth/client-metadata.json"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "client_id": "https://app.example.com/oauth/client-metadata.json",
            "client_name": "Example MCP Client",
            "redirect_uris": ["http://127.0.0.1:3000/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        mock_http_client.get.return_value = mock_response

        # WHEN
        metadata = await discovery_service.fetch_client_metadata(client_id)

        # THEN
        assert metadata.client_id == client_id
        assert metadata.client_name == "Example MCP Client"
        assert "http://127.0.0.1:3000/callback" in metadata.redirect_uris
        mock_http_client.get.assert_called_once_with(client_id, timeout=30)

    @pytest.mark.asyncio
    async def test_fetch_client_metadata_validates_client_id_matches_url(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Validates that client_id in document matches URL."""
        # GIVEN
        client_id = "https://app.example.com/oauth/client-metadata.json"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "client_id": "https://different.example.com/client.json",  # Mismatch!
            "client_name": "Example MCP Client",
            "redirect_uris": ["http://127.0.0.1:3000/callback"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN/THEN
        with pytest.raises(OAuth2DiscoveryError) as exc_info:
            await discovery_service.fetch_client_metadata(client_id)

        assert "client_id" in str(exc_info.value).lower()
        assert "mismatch" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_is_url_client_id_validates_format(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Validates URL-formatted client IDs."""
        # GIVEN
        valid_url_client_id = "https://app.example.com/oauth/client-metadata.json"
        invalid_client_ids = [
            "my-client-id",  # Not a URL
            "http://app.example.com/client.json",  # HTTP not HTTPS
            "https://app.example.com/",  # No path component
            "https://app.example.com",  # No path component
        ]

        # WHEN/THEN
        assert discovery_service.is_url_client_id(valid_url_client_id) is True
        for invalid_id in invalid_client_ids:
            assert discovery_service.is_url_client_id(invalid_id) is False

    @pytest.mark.asyncio
    async def test_validate_redirect_uri_against_metadata(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Validates redirect URIs against metadata document."""
        # GIVEN
        metadata = ClientMetadataDocument(
            client_id="https://app.example.com/oauth/client-metadata.json",
            client_name="Example Client",
            redirect_uris=[
                "http://127.0.0.1:3000/callback",
                "http://localhost:3000/callback",
            ],
        )

        # WHEN/THEN
        assert discovery_service.validate_redirect_uri("http://127.0.0.1:3000/callback", metadata) is True
        assert discovery_service.validate_redirect_uri("http://localhost:3000/callback", metadata) is True
        assert discovery_service.validate_redirect_uri("https://evil.com/callback", metadata) is False

    # =========================================================================
    # Resource Parameter Tests (RFC 8707)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_build_authorization_url_includes_resource(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Authorization URL includes resource parameter."""
        # GIVEN
        authorization_endpoint = "https://auth.example.com/authorize"
        client_id = "my-client"
        redirect_uri = "http://localhost:3000/callback"
        resource = "https://mcp.example.com"
        state = "random-state"
        code_challenge = "abc123"

        # WHEN
        url = discovery_service.build_authorization_url(
            authorization_endpoint=authorization_endpoint,
            client_id=client_id,
            redirect_uri=redirect_uri,
            resource=resource,
            state=state,
            code_challenge=code_challenge,
        )

        # THEN
        assert "resource=https%3A%2F%2Fmcp.example.com" in url
        assert "response_type=code" in url
        assert f"client_id={client_id}" in url
        assert f"state={state}" in url
        assert f"code_challenge={code_challenge}" in url
        assert "code_challenge_method=S256" in url

    @pytest.mark.asyncio
    async def test_build_token_request_includes_resource(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Token request includes resource parameter."""
        # GIVEN
        code = "authorization-code"
        redirect_uri = "http://localhost:3000/callback"
        resource = "https://mcp.example.com"
        code_verifier = "verifier123"
        client_id = "my-client"

        # WHEN
        params = discovery_service.build_token_request_params(
            grant_type="authorization_code",
            code=code,
            redirect_uri=redirect_uri,
            resource=resource,
            code_verifier=code_verifier,
            client_id=client_id,
        )

        # THEN
        assert params["resource"] == "https://mcp.example.com"
        assert params["grant_type"] == "authorization_code"
        assert params["code"] == code
        assert params["code_verifier"] == code_verifier
        assert params["client_id"] == client_id

    # =========================================================================
    # WWW-Authenticate Header Building Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_build_www_authenticate_header_401(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Builds WWW-Authenticate header for 401 response."""
        # GIVEN
        resource_metadata_url = "https://mcp.example.com/.well-known/oauth-protected-resource"
        scope = "files:read"

        # WHEN
        header = discovery_service.build_www_authenticate_header(
            resource_metadata=resource_metadata_url,
            scope=scope,
        )

        # THEN
        assert 'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"' in header
        assert 'scope="files:read"' in header
        assert header.startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_build_www_authenticate_header_403(
        self,
        discovery_service: OAuth2DiscoveryService,
    ) -> None:
        """Test: Builds WWW-Authenticate header for 403 insufficient scope."""
        # GIVEN
        resource_metadata_url = "https://mcp.example.com/.well-known/oauth-protected-resource"
        scope = "files:read files:write user:profile"

        # WHEN
        header = discovery_service.build_www_authenticate_header(
            resource_metadata=resource_metadata_url,
            scope=scope,
            error="insufficient_scope",
        )

        # THEN
        assert 'error="insufficient_scope"' in header
        assert 'scope="files:read files:write user:profile"' in header
        assert 'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"' in header

    # =========================================================================
    # Caching Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_authorization_server_metadata_is_cached(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Authorization server metadata is cached."""
        # GIVEN
        issuer_url = "https://auth.example.com"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": ["S256"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN - Call twice
        await discovery_service.discover_authorization_server(issuer_url)
        await discovery_service.discover_authorization_server(issuer_url)

        # THEN - HTTP should only be called once (cached)
        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_client_metadata_is_cached(
        self,
        discovery_service: OAuth2DiscoveryService,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test: Client metadata is cached."""
        # GIVEN
        client_id = "https://app.example.com/oauth/client-metadata.json"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "client_id": client_id,
            "client_name": "Example Client",
            "redirect_uris": ["http://127.0.0.1:3000/callback"],
        }
        mock_http_client.get.return_value = mock_response

        # WHEN - Call twice
        await discovery_service.fetch_client_metadata(client_id)
        await discovery_service.fetch_client_metadata(client_id)

        # THEN - HTTP should only be called once (cached)
        assert mock_http_client.get.call_count == 1
