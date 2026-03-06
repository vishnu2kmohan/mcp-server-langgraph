"""
Protected Resource Metadata Endpoint Tests

TDD: Tests written FIRST for the /.well-known/oauth-protected-resource endpoint.
Per RFC 9728 and MCP 2025-11-25, servers MUST expose this endpoint.
"""

import gc
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="protected_resource_endpoint"),
]


class TestProtectedResourceMetadataEndpoint:
    """TDD tests for Protected Resource Metadata endpoint per RFC 9728."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.mcp_server_url = "https://mcp.example.com"
        settings.keycloak_server_url = "https://auth.example.com"
        settings.keycloak_realm = "mcp"
        settings.mcp_scopes_supported = ["tools:read", "tools:execute", "resources:read"]
        return settings

    @pytest.fixture
    def test_client(self, mock_settings: MagicMock) -> TestClient:
        """Create test client with mocked settings."""
        from fastapi import FastAPI

        # Import here to avoid circular imports
        from mcp_server_langgraph.mcp.protected_resource import (
            create_protected_resource_router,
        )

        app = FastAPI()
        router = create_protected_resource_router(
            resource_url=mock_settings.mcp_server_url,
            authorization_servers=[f"{mock_settings.keycloak_server_url}/realms/{mock_settings.keycloak_realm}"],
            scopes_supported=mock_settings.mcp_scopes_supported,
        )
        app.include_router(router)

        return TestClient(app)

    # =========================================================================
    # RFC 9728 Compliance Tests
    # =========================================================================

    def test_well_known_endpoint_returns_200(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: /.well-known/oauth-protected-resource returns 200."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")

        # THEN
        assert response.status_code == 200

    def test_well_known_endpoint_returns_json(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Endpoint returns application/json content type."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")

        # THEN
        assert response.headers["content-type"] == "application/json"

    def test_well_known_endpoint_includes_resource(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Response includes resource identifier."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")
        data = response.json()

        # THEN
        assert "resource" in data
        assert data["resource"] == "https://mcp.example.com"

    def test_well_known_endpoint_includes_authorization_servers(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Response includes authorization_servers array."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")
        data = response.json()

        # THEN
        assert "authorization_servers" in data
        assert isinstance(data["authorization_servers"], list)
        assert len(data["authorization_servers"]) >= 1
        assert "https://auth.example.com/realms/mcp" in data["authorization_servers"]

    def test_well_known_endpoint_includes_scopes_supported(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Response includes scopes_supported array."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")
        data = response.json()

        # THEN
        assert "scopes_supported" in data
        assert isinstance(data["scopes_supported"], list)
        assert "tools:read" in data["scopes_supported"]
        assert "tools:execute" in data["scopes_supported"]
        assert "resources:read" in data["scopes_supported"]

    def test_well_known_endpoint_includes_bearer_methods(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Response includes bearer_methods_supported."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")
        data = response.json()

        # THEN
        assert "bearer_methods_supported" in data
        assert "header" in data["bearer_methods_supported"]

    # =========================================================================
    # Path-based Discovery Tests (RFC 9728 Section 3.1)
    # =========================================================================

    def test_path_based_well_known_endpoint(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test: Path-based discovery at /.well-known/oauth-protected-resource/path."""
        from fastapi import FastAPI

        from mcp_server_langgraph.mcp.protected_resource import (
            create_protected_resource_router,
        )

        app = FastAPI()
        router = create_protected_resource_router(
            resource_url="https://mcp.example.com/api/v1",
            authorization_servers=["https://auth.example.com"],
            scopes_supported=["api:read"],
            path_prefix="/api/v1",
        )
        app.include_router(router)
        client = TestClient(app)

        # WHEN
        response = client.get("/.well-known/oauth-protected-resource/api/v1")

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "https://mcp.example.com/api/v1"

    # =========================================================================
    # Cache Control Tests
    # =========================================================================

    def test_well_known_endpoint_has_cache_headers(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Endpoint includes appropriate cache headers."""
        # WHEN
        response = test_client.get("/.well-known/oauth-protected-resource")

        # THEN
        # Should have cache-control header for caching (e.g., 1 hour)
        assert "cache-control" in response.headers
        cache_control = response.headers["cache-control"]
        assert "max-age" in cache_control

    # =========================================================================
    # CORS Tests (for browser-based clients)
    # =========================================================================

    def test_well_known_endpoint_allows_cors(
        self,
        test_client: TestClient,
    ) -> None:
        """Test: Endpoint allows CORS for browser discovery."""
        # WHEN
        response = test_client.options(
            "/.well-known/oauth-protected-resource",
            headers={"Origin": "https://client.example.com"},
        )

        # THEN - Should allow the request (not 405 or 403)
        # CORS middleware would add Access-Control-Allow-Origin
        assert response.status_code in [200, 204]
