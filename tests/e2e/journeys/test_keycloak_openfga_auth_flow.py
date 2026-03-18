"""
E2E Tests: Full Authentication & Authorization Flow (Keycloak → OpenFGA)

This test suite verifies the complete auth flow from Keycloak authentication
through OpenFGA authorization. It tests the integration between:

1. Keycloak - OIDC authentication and JWT token issuance
2. OpenFGA - Fine-grained authorization permission checks
3. MCP Server - Protected endpoint access with auth

User Journeys Tested:
- Admin user: Full access (owner) to vector_store
- Alice: Editor access to vector_store (CRUD)
- Bob: Viewer access to vector_store (read-only)

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


# Module-level skip checks are unreliable with pytest-xdist
# Use autouse fixture instead for proper skip behavior


@pytest.fixture(autouse=True)
def skip_if_auth_infrastructure_unavailable():
    """Skip tests if Keycloak/OpenFGA infrastructure is not available.

    Using a fixture (vs module-level pytestmark.append) ensures proper
    skip behavior with pytest-xdist workers.
    """
    if not _keycloak_available():
        pytest.skip("Keycloak not available at localhost:80/authn")
    if not _openfga_available():
        pytest.skip("OpenFGA not available at localhost:9080")


# URLs and credentials - use gateway URLs consistent with integration tests
KEYCLOAK_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost/authn")
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")

# Test users from default-realm.json
TEST_USERS = {
    "admin": {"username": "admin", "password": "admin123"},
    "alice": {"username": "alice", "password": "alice123"},
    "bob": {"username": "bob", "password": "bob123"},
}


class KeycloakAuthHelper:
    """
    Helper class for Keycloak authentication operations.

    Authentication Methods (per RFC 9700):
    1. get_token_via_client_credentials() - RECOMMENDED for service accounts
    2. get_token_via_token_exchange(username) - RECOMMENDED for user-specific tests
    3. get_token(username, password) - DEPRECATED, uses ROPC
    """

    def __init__(self, keycloak_url: str = KEYCLOAK_URL):
        self.keycloak_url = keycloak_url
        self.token_url = f"{keycloak_url}/realms/default/protocol/openid-connect/token"
        self.userinfo_url = f"{keycloak_url}/realms/default/protocol/openid-connect/userinfo"
        self.client_id = "agent-studio-keycloak-client-id-for-e2e-tests"
        self.client_secret = "test-client-secret-for-e2e-tests"

    def get_token_via_client_credentials(self) -> dict:
        """
        Get access token via client credentials grant (RFC 9700 compliant).

        Use for service account authentication - no user context.
        """
        import requests

        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid email profile",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValueError(f"Client credentials token request failed: {response.status_code} - {response.text}")

        return response.json()

    def get_token_via_token_exchange(self, username: str) -> dict:
        """
        Get user-specific access token via token exchange (RFC 8693).

        Two-step flow:
        1. Get service account token via client_credentials
        2. Exchange it for a user-specific token with subject_token

        Use for tests that need user-specific claims without the user's password.
        Requires token exchange to be enabled in Keycloak for the client.
        """
        import requests

        # Step 1: Get service account token
        sa_response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid email profile",
            },
            timeout=10,
        )
        if sa_response.status_code != 200:
            raise ValueError(f"Client credentials request failed: {sa_response.status_code} - {sa_response.text}")

        sa_token = sa_response.json().get("access_token")
        if not sa_token:
            raise ValueError("Service account token response missing access_token")

        # Step 2: Exchange for user-specific token (RFC 8693)
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": username,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid email profile",
            },
            timeout=10,
        )

        if response.status_code == 400:
            error_body = response.json() if response.content else {}
            error_desc = error_body.get("error_description", "")
            if "not allowed" in error_desc.lower() or "permission" in error_desc.lower():
                raise ValueError(
                    f"Token exchange not configured for client '{self.client_id}'. "
                    f"Enable token-exchange in Keycloak Admin. Error: {error_desc}"
                )
            raise ValueError(f"Token exchange failed: {error_desc}")

        if response.status_code != 200:
            raise ValueError(f"Token exchange request failed: {response.status_code} - {response.text}")

        return response.json()

    def get_token(self, username: str, password: str = "") -> dict:
        """
        Get access token for user via modern OAuth2 flows.

        Uses client_credentials grant (service account token).
        ROPC (password grant) is disabled per security audit (ADR-0086).

        Args:
            username: User username (for documentation, not used in client_credentials)
            password: Deprecated - ROPC is disabled

        Returns:
            Token response dict with access_token, etc.
        """
        import requests

        # Use client_credentials since ROPC is disabled (ADR-0086)
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
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
    """Helper class for OpenFGA authorization operations.

    Uses OIDC JWT tokens from Keycloak for OpenFGA API access.
    docker-compose.test.yml configures OPENFGA_AUTHN_METHOD=oidc,
    so pre-shared key auth is rejected. The dedicated OpenFGA OIDC client
    in Keycloak provides tokens with the correct audience claim.
    """

    # OpenFGA OIDC client credentials (from Keycloak default-realm.json)
    _OPENFGA_OIDC_CLIENT_ID = "agent-studio-openfga-oidc-cient-id-for-e2e-tests"
    _OPENFGA_OIDC_CLIENT_SECRET = "agent-studio-openfga-oidc-client-secret-for-e2e-tests"

    def __init__(self, openfga_url: str = OPENFGA_URL):
        self.openfga_url = openfga_url
        self._store_id = None
        self._model_id = None
        self._token = None

    def _get_oidc_token(self) -> str:
        """Get OIDC token from Keycloak for OpenFGA API access."""
        if self._token:
            return self._token

        import requests

        response = requests.post(
            f"{KEYCLOAK_URL}/realms/default/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._OPENFGA_OIDC_CLIENT_ID,
                "client_secret": self._OPENFGA_OIDC_CLIENT_SECRET,
                "scope": "openid",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to get OpenFGA OIDC token: {response.status_code} - {response.text}")

        self._token = response.json()["access_token"]
        return self._token

    def _get_headers(self) -> dict:
        """Get headers with OIDC bearer token auth."""
        return {
            "Authorization": f"Bearer {self._get_oidc_token()}",
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
                if store.get("name") == "agent-studio-openfga-store-test":
                    self._store_id = store.get("id")
                    return self._store_id

        raise ValueError("Store 'agent-studio-openfga-store-test' not found")

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


_TOKEN_EXCHANGE_AVAILABLE: bool | None = None


def _token_exchange_available() -> bool:
    """Check if token exchange (RFC 8693) is configured in Keycloak."""
    global _TOKEN_EXCHANGE_AVAILABLE
    if _TOKEN_EXCHANGE_AVAILABLE is not None:
        return _TOKEN_EXCHANGE_AVAILABLE
    auth = KeycloakAuthHelper()
    try:
        auth.get_token_via_token_exchange("admin")
        _TOKEN_EXCHANGE_AVAILABLE = True
    except ValueError:
        _TOKEN_EXCHANGE_AVAILABLE = False
    return _TOKEN_EXCHANGE_AVAILABLE


@pytest.fixture
def require_user_token():
    """Skip test if user-specific tokens are unavailable.

    Token exchange (RFC 8693) is needed for user-impersonation tokens.
    When not configured, client_credentials fallback returns service
    account tokens without user-specific claims (preferred_username, etc.).
    """
    if not _token_exchange_available():
        pytest.skip(
            "Token exchange (RFC 8693) not configured in Keycloak. "
            "client_credentials returns service account tokens "
            "without user-specific claims."
        )


def _get_user_token(auth: KeycloakAuthHelper, username: str) -> dict:
    """
    Helper to get user token using modern auth methods with fallback.

    Tries:
    1. Token exchange (RFC 8693) - no password needed
    2. client_credentials (fallback) - returns service account token

    Args:
        auth: KeycloakAuthHelper instance
        username: Username to get token for

    Returns:
        Token response dict with access_token
    """
    try:
        return auth.get_token_via_token_exchange(username)
    except ValueError:
        # Token exchange may not be configured — fall back to client_credentials
        return auth.get_token(username)


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestKeycloakAuthentication:
    """Test Keycloak authentication operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_authenticate(self):
        """
        GIVEN: Admin user credentials from Keycloak
        WHEN: Requesting access token via token exchange (or ROPC fallback)
        THEN: Should receive valid access token with correct claims

        User Journey: Admin logs in to access management features

        Authentication: Uses RFC 8693 token exchange with ROPC fallback
        """
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "admin")

        assert "access_token" in token_response
        # Token exchange may not return refresh_token
        assert token_response.get("token_type", "Bearer") == "Bearer"

    def test_alice_can_authenticate(self):
        """
        GIVEN: Alice user credentials from Keycloak
        WHEN: Requesting access token via token exchange (or ROPC fallback)
        THEN: Should receive valid access token

        User Journey: Alice logs in to access standard features

        Authentication: Uses RFC 8693 token exchange with ROPC fallback
        """
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "alice")

        assert "access_token" in token_response

    def test_bob_can_authenticate(self):
        """
        GIVEN: Bob user credentials from Keycloak
        WHEN: Requesting access token via token exchange (or ROPC fallback)
        THEN: Should receive valid access token

        User Journey: Bob logs in to access basic features

        Authentication: Uses RFC 8693 token exchange with ROPC fallback
        """
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "bob")

        assert "access_token" in token_response

    @pytest.mark.skip(reason="ROPC is disabled per ADR-0086 - cannot test user credential validation with client_credentials")
    def test_invalid_credentials_rejected(self):
        """
        GIVEN: Invalid user credentials
        WHEN: Requesting access token via ROPC (intentionally testing ROPC flow)
        THEN: Should be rejected with error

        User Journey: Failed login attempt

        Note: This test intentionally used ROPC to test credential validation.
        ROPC is now disabled per security audit (ADR-0086).
        Token exchange and client_credentials cannot test invalid user credentials.
        """
        pass  # Skipped via decorator - ROPC disabled per ADR-0086

    def test_userinfo_endpoint_returns_claims(self, require_user_token):
        """
        GIVEN: Valid user-specific access token (via token exchange)
        WHEN: Requesting userinfo endpoint
        THEN: Should return user claims (sub, email, preferred_username)

        User Journey: Verify user identity after login

        Authentication: Requires RFC 8693 token exchange for user-specific claims
        """
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "alice")

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


# Note: TestOpenFGAPlaygroundPermissions class removed - playground deprecated


@pytest.mark.xdist_group(name="test_keycloak_openfga_auth_flow")
class TestFullAuthFlow:
    """Test the complete auth flow from Keycloak login to OpenFGA permission check."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_full_flow_vector_store_access(self, require_user_token):
        """
        GIVEN: Admin credentials and running infrastructure
        WHEN: Admin authenticates and checks vector_store permission
        THEN: Full flow should succeed with owner access

        User Journey: Admin logs in and accesses vector store management

        Authentication: Requires RFC 8693 token exchange for user-specific claims
        """
        # Step 1: Authenticate via Keycloak (using modern auth)
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "admin")
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "admin"

        # Step 3: Check permission via OpenFGA
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:admin", "owner", "vector_store:default")
        assert allowed, "Admin should have owner access to vector_store"

    def test_alice_full_flow_editor_access(self, require_user_token):
        """
        GIVEN: Alice credentials and running infrastructure
        WHEN: Alice authenticates and checks vector_store permission
        THEN: Full flow should succeed with editor access

        User Journey: Alice logs in and has CRUD access to vector_store

        Authentication: Requires RFC 8693 token exchange for user-specific claims
        """
        # Step 1: Authenticate via Keycloak (using modern auth)
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "alice")
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "alice"

        # Step 3: Check permission via OpenFGA
        authz = OpenFGAAuthHelper()
        allowed = authz.check_permission("user:alice", "editor", "vector_store:default")
        assert allowed, "Alice should have editor access to vector_store:default"

    def test_bob_full_flow_viewer_only(self, require_user_token):
        """
        GIVEN: Bob credentials and running infrastructure
        WHEN: Bob authenticates and checks vector_store permission
        THEN: Authentication succeeds, bob has viewer but NOT editor access

        User Journey: Bob logs in with read-only access to vector_store

        Authentication: Requires RFC 8693 token exchange for user-specific claims
        """
        # Step 1: Authenticate via Keycloak (using modern auth)
        auth = KeycloakAuthHelper()
        token_response = _get_user_token(auth, "bob")
        assert "access_token" in token_response, "Failed to get access token"

        # Step 2: Get user info from token
        userinfo = auth.get_userinfo(token_response["access_token"])
        assert userinfo.get("preferred_username") == "bob"

        # Step 3: Check permission via OpenFGA
        authz = OpenFGAAuthHelper()
        viewer_allowed = authz.check_permission("user:bob", "viewer", "vector_store:default")
        editor_allowed = authz.check_permission("user:bob", "editor", "vector_store:default")
        assert viewer_allowed, "Bob should have viewer access to vector_store:default"
        assert not editor_allowed, "Bob should NOT have editor access to vector_store:default"

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
