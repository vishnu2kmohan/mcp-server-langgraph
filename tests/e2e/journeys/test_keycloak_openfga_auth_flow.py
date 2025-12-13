"""
E2E Tests: Full Authentication & Authorization Flow (Keycloak → OpenFGA)

This test suite verifies the complete auth flow from Keycloak authentication
through OpenFGA authorization. It tests the integration between:

1. Keycloak - OIDC authentication and JWT token issuance
2. OpenFGA - Fine-grained authorization permission checks
3. MCP Server - Protected endpoint access with auth

User Journeys Tested:
- Admin user: Full access to vector_store and authz:playground
- Alice: Viewer access to vector_store and authz:playground
- Bob: Viewer access to vector_store, NO access to authz:playground

Reference: ADR-0068 - Gateway-Level Authentication

Prerequisites:
- Run `make test-infra-up` to start infrastructure
- openfga-seed-test container must have seeded permissions
"""

import gc
import os

import pytest

# Mark as E2E test requiring full infrastructure
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.auth_flow,
]


def _keycloak_available() -> bool:
    """Check if Keycloak is available via gateway."""
    try:
        import requests

        # Use gateway URL (port 80) with /authn prefix - consistent with integration tests
        response = requests.get(
            "http://localhost/authn/realms/default/.well-known/openid-configuration",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _openfga_available() -> bool:
    """Check if OpenFGA is available."""
    try:
        import requests

        # OpenFGA uses /healthz for health checks (not /health)
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip at module level if infrastructure not available
if not _keycloak_available() or not _openfga_available():
    pytestmark.append(pytest.mark.skip(reason="Auth infrastructure not available for E2E tests"))

# URLs and credentials - use gateway URLs consistent with integration tests
KEYCLOAK_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost/authn")
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")
OPENFGA_PRESHARED_KEY = os.getenv("OPENFGA_PRESHARED_KEY", "test-openfga-preshared-key")

# Test users from default-realm.json
TEST_USERS = {
    "admin": {"username": "admin", "password": "admin123"},
    "alice": {"username": "alice", "password": "alice123"},
    "bob": {"username": "bob", "password": "bob123"},
}


class KeycloakAuthHelper:
    """Helper class for Keycloak authentication operations."""

    def __init__(self, keycloak_url: str = KEYCLOAK_URL):
        self.keycloak_url = keycloak_url
        self.token_url = f"{keycloak_url}/realms/default/protocol/openid-connect/token"
        self.userinfo_url = f"{keycloak_url}/realms/default/protocol/openid-connect/userinfo"

    def get_token(self, username: str, password: str) -> dict:
        """Get access token for user via password grant."""
        import requests

        response = requests.post(
            self.token_url,
            data={
                "grant_type": "password",
                "client_id": "mcp-server",
                "client_secret": "test-client-secret-for-e2e-tests",
                "username": username,
                "password": password,
                "scope": "openid email profile",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValueError(f"Token request failed: {response.status_code} - {response.text}")

        return response.json()

    def get_userinfo(self, access_token: str) -> dict:
        """Get user info from access token."""
        import requests

        response = requests.get(
            self.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if response.status_code != 200:
            raise ValueError(f"Userinfo request failed: {response.status_code}")

        return response.json()


class OpenFGAAuthHelper:
    """Helper class for OpenFGA authorization operations."""

    def __init__(self, openfga_url: str = OPENFGA_URL, preshared_key: str = OPENFGA_PRESHARED_KEY):
        self.openfga_url = openfga_url
        self.preshared_key = preshared_key
        self._store_id = None
        self._model_id = None

    def _get_headers(self) -> dict:
        """Get headers with preshared key auth."""
        return {
            "Authorization": f"Bearer {self.preshared_key}",
            "Content-Type": "application/json",
        }

    def _get_store_id(self) -> str:
        """Get the seeded store ID."""
        if self._store_id:
            return self._store_id

        import requests

        response = requests.get(
            f"{self.openfga_url}/stores",
            headers=self._get_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            stores = response.json().get("stores", [])
            for store in stores:
                if store.get("name") == "mcp-server-langgraph-test":
                    self._store_id = store.get("id")
                    return self._store_id

        raise ValueError("Store 'mcp-server-langgraph-test' not found")

    def _get_model_id(self) -> str:
        """Get the latest authorization model ID."""
        if self._model_id:
            return self._model_id

        import requests

        store_id = self._get_store_id()
        response = requests.get(
            f"{self.openfga_url}/stores/{store_id}/authorization-models",
            headers=self._get_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            models = response.json().get("authorization_models", [])
            if models:
                self._model_id = models[0].get("id")
                return self._model_id

        raise ValueError("No authorization models found")

    def check_permission(self, user: str, relation: str, obj: str) -> bool:
        """Check if user has permission via OpenFGA."""
        import requests

        store_id = self._get_store_id()
        model_id = self._get_model_id()

        response = requests.post(
            f"{self.openfga_url}/stores/{store_id}/check",
            headers=self._get_headers(),
            json={
                "authorization_model_id": model_id,
                "tuple_key": {
                    "user": user,
                    "relation": relation,
                    "object": obj,
                },
            },
            timeout=10,
        )

        if response.status_code == 200:
            return response.json().get("allowed", False)
        return False


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestKeycloakAuthentication:
    """Test Keycloak authentication operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_authenticate(self):
        """
        GIVEN: Admin user credentials from Keycloak
        WHEN: Requesting access token via password grant
        THEN: Should receive valid access token with correct claims

        User Journey: Admin logs in to access management features
        """
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["admin"]["username"],
            TEST_USERS["admin"]["password"],
        )

        assert "access_token" in token_response
        assert "refresh_token" in token_response
        assert token_response.get("token_type") == "Bearer"

    def test_alice_can_authenticate(self):
        """
        GIVEN: Alice user credentials from Keycloak
        WHEN: Requesting access token via password grant
        THEN: Should receive valid access token

        User Journey: Alice logs in to access standard features
        """
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["alice"]["username"],
            TEST_USERS["alice"]["password"],
        )

        assert "access_token" in token_response
        assert "refresh_token" in token_response

    def test_bob_can_authenticate(self):
        """
        GIVEN: Bob user credentials from Keycloak
        WHEN: Requesting access token via password grant
        THEN: Should receive valid access token

        User Journey: Bob logs in to access basic features
        """
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["bob"]["username"],
            TEST_USERS["bob"]["password"],
        )

        assert "access_token" in token_response
        assert "refresh_token" in token_response

    def test_invalid_credentials_rejected(self):
        """
        GIVEN: Invalid user credentials
        WHEN: Requesting access token
        THEN: Should be rejected with error

        User Journey: Failed login attempt
        """
        auth = KeycloakAuthHelper()

        with pytest.raises(ValueError, match="Token request failed"):
            auth.get_token("invalid_user", "wrong_password")

    def test_userinfo_endpoint_returns_claims(self):
        """
        GIVEN: Valid access token
        WHEN: Requesting userinfo endpoint
        THEN: Should return user claims (sub, email, preferred_username)

        User Journey: Verify user identity after login
        """
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["alice"]["username"],
            TEST_USERS["alice"]["password"],
        )

        userinfo = auth.get_userinfo(token_response["access_token"])

        assert "sub" in userinfo, "Missing 'sub' claim"
        assert userinfo.get("preferred_username") == "alice"


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestOpenFGAVectorStorePermissions:
    """Test OpenFGA permissions for vector_store resource."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_has_owner_on_vector_store(self):
        """
        GIVEN: Admin user authenticated
        WHEN: Checking owner permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Admin manages vector store collections
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:admin", "owner", "vector_store:default")
        assert allowed, "Admin should have owner permission on vector_store:default"

    def test_alice_has_viewer_on_vector_store(self):
        """
        GIVEN: Alice user authenticated
        WHEN: Checking viewer permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Alice can search vector store
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:alice", "viewer", "vector_store:default")
        assert allowed, "Alice should have viewer permission on vector_store:default"

    def test_bob_has_viewer_on_vector_store(self):
        """
        GIVEN: Bob user authenticated
        WHEN: Checking viewer permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Bob can search vector store
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:bob", "viewer", "vector_store:default")
        assert allowed, "Bob should have viewer permission on vector_store:default"

    def test_alice_cannot_own_vector_store(self):
        """
        GIVEN: Alice user authenticated
        WHEN: Checking owner permission on vector_store:default
        THEN: Should return allowed=false (alice only has viewer)

        User Journey: Alice tries to manage collections (denied)
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:alice", "owner", "vector_store:default")
        assert not allowed, "Alice should NOT have owner permission on vector_store:default"


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestOpenFGAPlaygroundPermissions:
    """Test OpenFGA permissions for authz:playground resource."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_has_admin_on_authz_playground(self):
        """
        GIVEN: Admin user authenticated
        WHEN: Checking admin permission on authz:playground
        THEN: Should return allowed=true

        User Journey: Admin can access OpenFGA Playground
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:admin", "admin", "authz:playground")
        assert allowed, "Admin should have admin permission on authz:playground"

    def test_alice_has_viewer_on_authz_playground(self):
        """
        GIVEN: Alice user authenticated
        WHEN: Checking viewer permission on authz:playground
        THEN: Should return allowed=true

        User Journey: Alice can view OpenFGA Playground (read-only)
        """
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:alice", "viewer", "authz:playground")
        assert allowed, "Alice should have viewer permission on authz:playground"

    def test_bob_denied_access_to_authz_playground(self):
        """
        GIVEN: Bob user authenticated
        WHEN: Checking any permission on authz:playground
        THEN: Should return allowed=false

        User Journey: Bob cannot access OpenFGA Playground (intentionally excluded)
        """
        authz = OpenFGAAuthHelper()

        admin_allowed = authz.check_permission("user:bob", "admin", "authz:playground")
        viewer_allowed = authz.check_permission("user:bob", "viewer", "authz:playground")

        assert not admin_allowed, "Bob should NOT have admin permission on authz:playground"
        assert not viewer_allowed, "Bob should NOT have viewer permission on authz:playground"


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestFullAuthFlow:
    """Test the complete auth flow from Keycloak login to OpenFGA permission check."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_full_flow_vector_store_access(self):
        """
        GIVEN: Admin credentials and running infrastructure
        WHEN: Admin authenticates and checks vector_store permission
        THEN: Full flow should succeed with owner access

        User Journey: Admin logs in and accesses vector store management
        """
        # Step 1: Authenticate via Keycloak
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["admin"]["username"],
            TEST_USERS["admin"]["password"],
        )
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "admin"

        # Step 3: Check permission via OpenFGA
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:admin", "owner", "vector_store:default")
        assert allowed, "Admin should have owner access to vector_store"

    def test_alice_full_flow_playground_access(self):
        """
        GIVEN: Alice credentials and running infrastructure
        WHEN: Alice authenticates and checks playground permission
        THEN: Full flow should succeed with viewer access

        User Journey: Alice logs in and views OpenFGA Playground
        """
        # Step 1: Authenticate via Keycloak
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["alice"]["username"],
            TEST_USERS["alice"]["password"],
        )
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "alice"

        # Step 3: Check permission via OpenFGA
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:alice", "viewer", "authz:playground")
        assert allowed, "Alice should have viewer access to authz:playground"

    def test_bob_full_flow_denied_playground(self):
        """
        GIVEN: Bob credentials and running infrastructure
        WHEN: Bob authenticates and checks playground permission
        THEN: Authentication succeeds but authorization fails

        User Journey: Bob logs in but cannot access OpenFGA Playground
        """
        # Step 1: Authenticate via Keycloak (should succeed)
        auth = KeycloakAuthHelper()
        token_response = auth.get_token(
            TEST_USERS["bob"]["username"],
            TEST_USERS["bob"]["password"],
        )
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "bob"

        # Step 3: Check permission via OpenFGA (should fail)
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:bob", "viewer", "authz:playground")
        assert not allowed, "Bob should NOT have access to authz:playground"

    def test_organization_membership_flow(self):
        """
        GIVEN: All test users authenticated
        WHEN: Checking organization membership
        THEN: All users should be members of organization:acme

        User Journey: Users belong to the same organization
        """
        authz = OpenFGAAuthHelper()

        for username in ["admin", "alice", "bob"]:
            allowed = authz.check_permission(f"user:{username}", "member", "organization:acme")
            assert allowed, f"{username} should be member of organization:acme"

    def test_tool_execution_permission_flow(self):
        """
        GIVEN: All test users authenticated
        WHEN: Checking tool:chat execution permission
        THEN: All users should be able to execute chat tool

        User Journey: All users can use the chat tool
        """
        authz = OpenFGAAuthHelper()

        for username in ["admin", "alice", "bob"]:
            allowed = authz.check_permission(f"user:{username}", "executor", "tool:chat")
            assert allowed, f"{username} should be able to execute tool:chat"
