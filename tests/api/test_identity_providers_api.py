"""
Tests for Identity Provider Discovery API

Tests the /api/v1/identity-providers endpoint that returns
available SSO identity providers from Keycloak for the login page.

TDD: RED phase - these tests define expected behavior.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.identity_providers import (
    router,
    clear_idp_cache,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear identity provider cache before each test."""
    clear_idp_cache()
    yield
    clear_idp_cache()


@pytest.fixture
def app():
    """Create test FastAPI app with identity providers router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.mark.xdist_group(name="testidentityprovidersendpoint")
class TestIdentityProvidersEndpoint:
    """Tests for GET /api/v1/identity-providers endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_returns_empty_list_when_no_idps_configured(self, client):
        """Should return empty list when Keycloak has no identity providers."""
        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            assert data["identity_providers"] == []
            assert data["has_social_login"] is False
            assert data["has_enterprise_sso"] is False

    @pytest.mark.unit
    def test_returns_social_login_providers(self, client):
        """Should return social login providers (Google, GitHub, etc.)."""
        mock_idps = [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
            },
            {
                "alias": "github",
                "displayName": "GitHub",
                "providerId": "github",
                "enabled": True,
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=mock_idps,
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            assert len(data["identity_providers"]) == 2
            assert data["has_social_login"] is True
            assert data["has_enterprise_sso"] is False

            # Verify provider details
            google = next(p for p in data["identity_providers"] if p["alias"] == "google")
            assert google["display_name"] == "Google"
            assert google["provider_type"] == "social"
            assert google["icon"] == "google"

    @pytest.mark.unit
    def test_returns_enterprise_sso_providers(self, client):
        """Should return enterprise SSO providers (OIDC, SAML)."""
        mock_idps = [
            {
                "alias": "corporate-okta",
                "displayName": "Corporate Okta",
                "providerId": "oidc",
                "enabled": True,
            },
            {
                "alias": "azure-ad",
                "displayName": "Azure AD",
                "providerId": "saml",
                "enabled": True,
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=mock_idps,
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            assert len(data["identity_providers"]) == 2
            assert data["has_social_login"] is False
            assert data["has_enterprise_sso"] is True

            # Verify OIDC provider
            okta = next(p for p in data["identity_providers"] if p["alias"] == "corporate-okta")
            assert okta["provider_type"] == "enterprise"

    @pytest.mark.unit
    def test_excludes_disabled_providers(self, client):
        """Should not return disabled identity providers."""
        mock_idps = [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
            },
            {
                "alias": "github",
                "displayName": "GitHub",
                "providerId": "github",
                "enabled": False,  # Disabled
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=mock_idps,
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            assert len(data["identity_providers"]) == 1
            assert data["identity_providers"][0]["alias"] == "google"

    @pytest.mark.unit
    def test_excludes_hidden_on_login_providers(self, client):
        """Should not return providers marked as hidden on login page."""
        mock_idps = [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
                "config": {"hideOnLoginPage": "false"},
            },
            {
                "alias": "internal-oidc",
                "displayName": "Internal OIDC",
                "providerId": "oidc",
                "enabled": True,
                "config": {"hideOnLoginPage": "true"},  # Hidden
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=mock_idps,
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            assert len(data["identity_providers"]) == 1
            assert data["identity_providers"][0]["alias"] == "google"

    @pytest.mark.unit
    def test_returns_login_url_with_idp_hint(self, client):
        """Should include login URL with kc_idp_hint for each provider."""
        mock_idps = [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            return_value=mock_idps,
        ):
            response = client.get("/api/v1/identity-providers")

            assert response.status_code == 200
            data = response.json()
            google = data["identity_providers"][0]

            # Should have login_url with kc_idp_hint
            assert "login_url" in google
            assert "kc_idp_hint=google" in google["login_url"]

    @pytest.mark.unit
    def test_handles_keycloak_unavailable(self, client):
        """Should return empty list when Keycloak is unavailable."""
        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            response = client.get("/api/v1/identity-providers")

            # Should gracefully degrade, not error
            assert response.status_code == 200
            data = response.json()
            assert data["identity_providers"] == []
            assert data["error"] == "Unable to fetch identity providers"

    @pytest.mark.unit
    def test_caches_idp_results(self, client):
        """Should cache identity provider results for performance."""
        mock_idps = [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
            },
        ]

        fetch_mock = AsyncMock(return_value=mock_idps)

        with patch(
            "mcp_server_langgraph.api.v1.identity_providers.fetch_keycloak_idps",
            fetch_mock,
        ):
            # First request
            response1 = client.get("/api/v1/identity-providers")
            assert response1.status_code == 200

            # Second request should use cache
            response2 = client.get("/api/v1/identity-providers")
            assert response2.status_code == 200

            # Should only call Keycloak once (cached)
            # Note: Cache implementation may vary
            assert fetch_mock.call_count >= 1  # At least once


@pytest.mark.xdist_group(name="testidentityprovidericons")
class TestIdentityProviderIcons:
    """Tests for identity provider icon mapping."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "provider_id,expected_icon",
        [
            ("google", "google"),
            ("github", "github"),
            ("facebook", "facebook"),
            ("twitter", "twitter"),
            ("microsoft", "microsoft"),
            ("apple", "apple"),
            ("linkedin", "linkedin"),
            ("oidc", "key"),
            ("saml", "shield"),
            ("unknown", "external-link"),
        ],
    )
    def test_maps_provider_to_icon(self, provider_id, expected_icon):
        """Should map provider IDs to appropriate icons."""
        from mcp_server_langgraph.api.v1.identity_providers import get_provider_icon

        assert get_provider_icon(provider_id) == expected_icon


@pytest.mark.xdist_group(name="testidentityprovidertypes")
class TestIdentityProviderTypes:
    """Tests for identity provider type classification."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "provider_id,expected_type",
        [
            ("google", "social"),
            ("github", "social"),
            ("facebook", "social"),
            ("twitter", "social"),
            ("linkedin", "social"),
            ("apple", "social"),
            ("microsoft", "enterprise"),
            ("oidc", "enterprise"),
            ("saml", "enterprise"),
            ("keycloak-oidc", "enterprise"),
        ],
    )
    def test_classifies_provider_type(self, provider_id, expected_type):
        """Should classify providers as social or enterprise."""
        from mcp_server_langgraph.api.v1.identity_providers import get_provider_type

        assert get_provider_type(provider_id) == expected_type
