"""
Integration tests for OpenFGA OIDC Authentication.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. OpenFGA API rejects requests without OIDC tokens
2. OpenFGA API accepts requests with valid OIDC tokens from Keycloak
3. OpenFGAClient obtains OIDC tokens using client credentials grant
4. OIDC tokens are cached and reused until near expiration
5. Expired tokens are automatically refreshed

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

import asyncio
import gc
import os
import time

import httpx
import pytest

from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.openfga,
    pytest.mark.oidc,
]

# URLs and credentials from .env.test
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost/authn")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "default")
OPENFGA_OIDC_CLIENT_ID = os.getenv("OPENFGA_OIDC_CLIENT_ID", "openfga-server")
OPENFGA_OIDC_CLIENT_SECRET = os.getenv("OPENFGA_OIDC_CLIENT_SECRET", "test-openfga-server-secret")

# Construct OIDC issuer URL
OIDC_ISSUER = f"{KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}"
TOKEN_ENDPOINT = f"{OIDC_ISSUER}/protocol/openid-connect/token"


# PYTEST-XDIST FIX: OpenFGA OIDC tests require real infrastructure (OpenFGA, Keycloak)
# that may not be properly available in parallel execution due to timing issues
_XDIST_OIDC_INFRASTRUCTURE_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


@pytest.mark.xdist_group(name="test_openfga_oidc")
class TestOpenFGAOIDCAuthentication:
    """Test OpenFGA OIDC authentication flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_unauthenticated_request_is_rejected(self):
        """
        GIVEN: No authentication header
        WHEN: Accessing OpenFGA stores endpoint
        THEN: Should return 401 Unauthorized

        User Journey: Unauthenticated request is blocked by OIDC validation
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OPENFGA_URL}/stores",
                timeout=10.0,
            )

        # Should reject unauthenticated requests
        assert response.status_code == 401, f"Expected 401 Unauthorized without OIDC token, got {response.status_code}"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_invalid_oidc_token_is_rejected(self):
        """
        GIVEN: Invalid OIDC token in Authorization header
        WHEN: Accessing OpenFGA stores endpoint
        THEN: Should return 401 Unauthorized

        User Journey: Request with invalid token is blocked
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OPENFGA_URL}/stores",
                headers={"Authorization": "Bearer invalid-token-should-fail"},
                timeout=10.0,
            )

        # Should reject invalid token
        assert response.status_code == 401, f"Expected 401 Unauthorized with invalid token, got {response.status_code}"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_obtain_oidc_token_from_keycloak(self):
        """
        GIVEN: Valid OIDC client credentials
        WHEN: Requesting access token via client credentials grant
        THEN: Should receive valid access token

        User Journey: Service obtains access token for machine-to-machine auth
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "client_credentials",
                    "client_id": OPENFGA_OIDC_CLIENT_ID,
                    "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
                },
                timeout=10.0,
            )

        # Should successfully obtain token
        assert response.status_code == 200, f"Expected 200 OK from token endpoint, got {response.status_code}: {response.text}"

        # Verify token response structure
        token_data = response.json()
        assert "access_token" in token_data, f"Expected 'access_token' in response, got: {token_data}"
        assert "expires_in" in token_data, f"Expected 'expires_in' in response, got: {token_data}"
        assert "token_type" in token_data, f"Expected 'token_type' in response, got: {token_data}"
        assert token_data["token_type"].lower() == "bearer", f"Expected token_type 'Bearer', got {token_data['token_type']}"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_valid_oidc_token_is_accepted_by_openfga(self):
        """
        GIVEN: Valid OIDC access token from Keycloak
        WHEN: Accessing OpenFGA stores endpoint with token
        THEN: Should return 200 OK with stores list

        User Journey: Authenticated service can access OpenFGA API
        """
        # First obtain OIDC token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "client_credentials",
                    "client_id": OPENFGA_OIDC_CLIENT_ID,
                    "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
                },
                timeout=10.0,
            )
            assert token_response.status_code == 200
            access_token = token_response.json()["access_token"]

            # Use token to access OpenFGA
            openfga_response = await client.get(
                f"{OPENFGA_URL}/stores",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

        # Should accept valid OIDC token
        assert openfga_response.status_code == 200, (
            f"Expected 200 OK with valid OIDC token, got {openfga_response.status_code}: {openfga_response.text}"
        )

        # Response should be valid JSON with stores
        data = openfga_response.json()
        assert "stores" in data, f"Expected 'stores' in response, got: {data}"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_openfga_client_obtains_oidc_token_automatically(self):
        """
        GIVEN: OpenFGAClient configured with OIDC credentials
        WHEN: Client makes its first API call
        THEN: Should automatically obtain and use OIDC token

        User Journey: Application uses OpenFGAClient without manual token management
        """
        config = OpenFGAConfig(
            api_url=OPENFGA_URL,
            store_name="mcp-server-langgraph-test",
            oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
            oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
            oidc_issuer=OIDC_ISSUER,
        )

        client = OpenFGAClient(config=config)

        try:
            # Initialize client (triggers OIDC token acquisition)
            await client._ensure_initialized()

            # Verify client has obtained and cached OIDC token
            assert client._oidc_access_token is not None, "Expected OIDC token to be cached"
            assert client._oidc_token_expires_at is not None, "Expected token expiration time to be cached"
            assert client._oidc_token_expires_at > time.time(), "Token should not be expired"

            # Verify client can make authenticated API calls
            # Use list_objects as a simple API call that requires authentication
            stores_response = await client._client.list_stores()
            assert stores_response is not None, "Expected valid response from OpenFGA API"

        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_openfga_client_caches_oidc_token(self):
        """
        GIVEN: OpenFGAClient that has obtained an OIDC token
        WHEN: Making multiple API calls
        THEN: Should reuse cached token instead of requesting new one each time

        User Journey: Efficient token management reduces Keycloak load
        """
        config = OpenFGAConfig(
            api_url=OPENFGA_URL,
            store_name="mcp-server-langgraph-test",
            oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
            oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
            oidc_issuer=OIDC_ISSUER,
        )

        client = OpenFGAClient(config=config)

        try:
            # First call - obtains token
            await client._ensure_initialized()
            first_token = client._oidc_access_token
            first_expiry = client._oidc_token_expires_at

            # Small delay to ensure time passes
            await asyncio.sleep(0.1)

            # Second call - should reuse cached token
            token2 = await client._get_oidc_access_token()

            # Verify same token is returned (cached)
            assert token2 == first_token, "Expected cached token to be reused"
            assert client._oidc_token_expires_at == first_expiry, "Token expiry should not change"

        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_openfga_client_refreshes_expired_token(self):
        """
        GIVEN: OpenFGAClient with an expired cached token
        WHEN: Making an API call
        THEN: Should automatically refresh the token

        User Journey: Token refresh happens transparently without service interruption

        Note: This test simulates expiration by setting a very short TTL
        """
        config = OpenFGAConfig(
            api_url=OPENFGA_URL,
            store_name="mcp-server-langgraph-test",
            oidc_client_id=OPENFGA_OIDC_CLIENT_ID,
            oidc_client_secret=OPENFGA_OIDC_CLIENT_SECRET,
            oidc_issuer=OIDC_ISSUER,
        )

        client = OpenFGAClient(config=config)

        try:
            # Get initial token
            await client._ensure_initialized()
            first_token = client._oidc_access_token

            # Simulate token expiration by setting expiry time in the past
            client._oidc_token_expires_at = time.time() - 60  # Expired 60 seconds ago

            # Request token again - should refresh
            new_token = await client._get_oidc_access_token()

            # Verify new token was obtained
            assert new_token is not None, "Expected new token to be obtained"
            assert new_token != first_token, "Expected different token after refresh"
            assert client._oidc_token_expires_at > time.time(), "New token should not be expired"

        finally:
            await client.close()


@pytest.mark.xdist_group(name="test_openfga_oidc")
class TestOpenFGAOIDCWriteOperations:
    """Test OpenFGA write operations with OIDC authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        _XDIST_OIDC_INFRASTRUCTURE_UNSTABLE,
        reason="OpenFGA/Keycloak infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_create_store_with_oidc_token(self):
        """
        GIVEN: Valid OIDC access token
        WHEN: Creating a new store via POST
        THEN: Should successfully create the store

        User Journey: Application creates authorization store using OIDC auth
        """
        # Obtain OIDC token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "client_credentials",
                    "client_id": OPENFGA_OIDC_CLIENT_ID,
                    "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
                },
                timeout=10.0,
            )
            assert token_response.status_code == 200
            access_token = token_response.json()["access_token"]

            # Create store with OIDC token
            response = await client.post(
                f"{OPENFGA_URL}/stores",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"name": "test-oidc-store"},
                timeout=10.0,
            )

        # Should successfully create store
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"

        data = response.json()
        assert "id" in data, f"Expected 'id' in response, got: {data}"
        assert data.get("name") == "test-oidc-store"

        # Cleanup: Delete the test store
        store_id = data["id"]
        async with httpx.AsyncClient() as client:
            cleanup_response = await client.delete(
                f"{OPENFGA_URL}/stores/{store_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            assert cleanup_response.status_code in [200, 204], f"Cleanup failed: {cleanup_response.status_code}"
