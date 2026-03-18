"""
Integration tests for Connection API Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Connection resources (/api/v1/connections)
2. MCP connection ownership and access

RED PHASE: These tests will initially FAIL because:
- connection resource type is NOT in model.json
- No connection:* tuples exist in sample-tuples.json

User Journeys:
- Admin: owner of connection:admin_conn (full CRUD)
- Alice: owner of connection:alice_conn (full CRUD on own)
- Bob: owner of connection:bob_conn (full CRUD on own)

Reference: Plan - Phase 5.2: Connections API
"""

import gc
import os

import pytest
import requests

# Mark as integration test requiring docker infrastructure
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.openfga,
    pytest.mark.connections,
]


# URLs and credentials
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")
# OIDC credentials for OpenFGA API access (ADR-0070: OIDC replaces preshared key)
OPENFGA_OIDC_CLIENT_ID = os.getenv("OPENFGA_OIDC_CLIENT_ID", "agent-studio-openfga-oidc-cient-id-for-e2e-tests")
OPENFGA_OIDC_CLIENT_SECRET = os.getenv("OPENFGA_OIDC_CLIENT_SECRET", "agent-studio-openfga-oidc-client-secret-for-e2e-tests")
KEYCLOAK_TOKEN_URL = os.getenv(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost/authn/realms/default/protocol/openid-connect/token",
)
_cached_oidc_token: str | None = None


def _get_oidc_token() -> str | None:
    """Obtain OIDC token from Keycloak for OpenFGA API access."""
    global _cached_oidc_token
    if _cached_oidc_token:
        return _cached_oidc_token
    try:
        response = requests.post(
            KEYCLOAK_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OPENFGA_OIDC_CLIENT_ID,
                "client_secret": OPENFGA_OIDC_CLIENT_SECRET,
            },
            timeout=10,
        )
        if response.status_code == 200:
            _cached_oidc_token = response.json().get("access_token")
            return _cached_oidc_token
    except Exception:
        pass
    return None


def _get_auth_headers() -> dict[str, str]:
    """Get OIDC authentication headers for OpenFGA API requests."""
    token = _get_oidc_token()
    if not token:
        pytest.skip("Could not obtain OIDC token from Keycloak for OpenFGA API access")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_openfga_store_and_model() -> tuple[str | None, str | None]:
    """Dynamically discover OpenFGA store and model IDs."""
    headers = _get_auth_headers()

    try:
        stores_resp = requests.get(f"{OPENFGA_URL}/stores", headers=headers, timeout=10)
        if stores_resp.status_code != 200:
            return None, None

        stores = stores_resp.json().get("stores", [])
        store_id = None
        for store in stores:
            if store.get("name") == "agent-studio-openfga-store-test":
                store_id = store.get("id")
                break

        if not store_id:
            return None, None

        models_resp = requests.get(
            f"{OPENFGA_URL}/stores/{store_id}/authorization-models",
            headers=headers,
            timeout=10,
        )
        if models_resp.status_code != 200:
            return store_id, None

        models = models_resp.json().get("authorization_models", [])
        if not models:
            return store_id, None

        model_id = models[0].get("id")
        return store_id, model_id

    except Exception:
        return None, None


def _check_permission(user: str, relation: str, obj: str) -> bool:
    """Check if user has permission via OpenFGA."""
    store_id, model_id = _get_openfga_store_and_model()
    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized")

    headers = _get_auth_headers()

    response = requests.post(
        f"{OPENFGA_URL}/stores/{store_id}/check",
        headers=headers,
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


@pytest.mark.xdist_group(name="test_connection_authorization")
class TestConnectionOwnership:
    """
    Test connection ownership authorization.

    Each user owns their own connections.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_owns_admin_connection(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner connection:admin_conn
        WHEN: Checking admin's owner permission
        THEN: Should return allowed=true

        User Journey: Admin can manage their MCP connections
        API Endpoint: DELETE /api/v1/connections/{id}
        """
        allowed = _check_permission("user:admin", "owner", "connection:admin_conn")
        assert allowed, "Admin should be owner of connection:admin_conn"

    def test_alice_owns_alice_connection(self):
        """
        GIVEN: Pre-seeded tuple user:alice owner connection:alice_conn
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=true

        User Journey: Alice can manage her MCP connections
        API Endpoint: PUT /api/v1/connections/{id}
        """
        allowed = _check_permission("user:alice", "owner", "connection:alice_conn")
        assert allowed, "Alice should be owner of connection:alice_conn"

    def test_bob_owns_bob_connection(self):
        """
        GIVEN: Pre-seeded tuple user:bob owner connection:bob_conn
        WHEN: Checking bob's owner permission
        THEN: Should return allowed=true

        User Journey: Bob can manage his MCP connections
        """
        allowed = _check_permission("user:bob", "owner", "connection:bob_conn")
        assert allowed, "Bob should be owner of connection:bob_conn"


@pytest.mark.xdist_group(name="test_connection_authorization")
class TestConnectionIsolation:
    """
    Test that users cannot access other users' connections.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_cannot_own_admin_connection(self):
        """
        GIVEN: Alice has no tuple for connection:admin_conn
        WHEN: Checking alice's owner permission on admin's connection
        THEN: Should return allowed=false

        User Journey: Users cannot manage other users' connections
        """
        allowed = _check_permission("user:alice", "owner", "connection:admin_conn")
        assert not allowed, "Alice should NOT be able to own admin's connection"

    def test_bob_cannot_own_alice_connection(self):
        """
        GIVEN: Bob has no tuple for connection:alice_conn
        WHEN: Checking bob's owner permission on alice's connection
        THEN: Should return allowed=false

        User Journey: Connections are private to their owners
        """
        allowed = _check_permission("user:bob", "owner", "connection:alice_conn")
        assert not allowed, "Bob should NOT be able to own alice's connection"

    def test_bob_cannot_view_alice_connection(self):
        """
        GIVEN: Bob has no viewer tuple for connection:alice_conn
        WHEN: Checking bob's viewer permission on alice's connection
        THEN: Should return allowed=false

        User Journey: Connections are not viewable by others
        API Endpoint: GET /api/v1/connections/{id} should fail for bob on alice's conn
        """
        allowed = _check_permission("user:bob", "viewer", "connection:alice_conn")
        assert not allowed, "Bob should NOT be able to view alice's connection"


@pytest.mark.xdist_group(name="test_connection_authorization")
class TestConnectionViewerAccess:
    """
    Test connection viewer authorization.

    Owners should automatically have viewer access via inheritance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_view_own_connection(self):
        """
        GIVEN: Admin is owner of connection:admin_conn
        WHEN: Checking admin's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Owners can always view their connections
        """
        allowed = _check_permission("user:admin", "viewer", "connection:admin_conn")
        assert allowed, "Admin should be viewer (via owner inheritance) of connection:admin_conn"

    def test_alice_can_view_own_connection(self):
        """
        GIVEN: Alice is owner of connection:alice_conn
        WHEN: Checking alice's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Alice can view her connections
        API Endpoint: GET /api/v1/connections/{id}
        """
        allowed = _check_permission("user:alice", "viewer", "connection:alice_conn")
        assert allowed, "Alice should be viewer (via owner inheritance) of connection:alice_conn"

    def test_bob_can_view_own_connection(self):
        """
        GIVEN: Bob is owner of connection:bob_conn
        WHEN: Checking bob's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Bob can view his connections
        """
        allowed = _check_permission("user:bob", "viewer", "connection:bob_conn")
        assert allowed, "Bob should be viewer (via owner inheritance) of connection:bob_conn"


@pytest.mark.xdist_group(name="test_connection_authorization")
class TestSharedConnectionAccess:
    """
    Test shared connection access patterns.

    Connections can be shared with viewers for collaboration.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_can_view_shared_connection(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer connection:shared_conn
        WHEN: Checking alice's viewer permission on shared connection
        THEN: Should return allowed=true

        User Journey: Alice can view connections shared with her
        """
        allowed = _check_permission("user:alice", "viewer", "connection:shared_conn")
        assert allowed, "Alice should be viewer of connection:shared_conn"

    def test_bob_can_view_shared_connection(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer connection:shared_conn
        WHEN: Checking bob's viewer permission on shared connection
        THEN: Should return allowed=true

        User Journey: Bob can view connections shared with him
        """
        allowed = _check_permission("user:bob", "viewer", "connection:shared_conn")
        assert allowed, "Bob should be viewer of connection:shared_conn"

    def test_alice_cannot_own_shared_connection(self):
        """
        GIVEN: Alice only has viewer access to shared_conn
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot delete shared connections
        """
        allowed = _check_permission("user:alice", "owner", "connection:shared_conn")
        assert not allowed, "Alice should NOT be owner of connection:shared_conn"
