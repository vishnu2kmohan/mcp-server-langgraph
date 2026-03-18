"""
Integration tests for OpenFGA Seeding Flow.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that the full OpenFGA seeding flow works correctly:
1. Store is created by openfga-seed-test container
2. Authorization model is uploaded from config/openfga/model.json
3. Relationship tuples are seeded from config/openfga/sample-tuples.json
4. Permission checks work correctly for all test users

Prerequisites:
- Run `make test-infra-up` to start infrastructure including openfga-seed-test
- The seeding container runs automatically and seeds OpenFGA

Reference: ADR-0068 - Gateway-Level Authentication
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
]


def _openfga_available() -> bool:
    """Check if OpenFGA is available and seeded."""
    try:
        # OpenFGA uses /healthz for health checks (not /health)
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Infrastructure check and autouse skip fixture are in tests/integration/auth/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)

# URLs and credentials
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")
EXPECTED_STORE_NAME = "agent-studio-openfga-store-test"

# OIDC credentials for OpenFGA API access (ADR-0070: OIDC replaces preshared key)
OPENFGA_OIDC_CLIENT_ID = os.getenv("OPENFGA_OIDC_CLIENT_ID", "agent-studio-openfga-oidc-cient-id-for-e2e-tests")
OPENFGA_OIDC_CLIENT_SECRET = os.getenv("OPENFGA_OIDC_CLIENT_SECRET", "agent-studio-openfga-oidc-client-secret-for-e2e-tests")
KEYCLOAK_TOKEN_URL = os.getenv(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost/authn/realms/default/protocol/openid-connect/token",
)

# Cache OIDC token at module level to avoid repeated Keycloak calls
_cached_oidc_token: str | None = None


def _get_oidc_token() -> str | None:
    """Obtain OIDC token from Keycloak using client credentials grant."""
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


def _get_store_id() -> str | None:
    """Get the seeded store ID by name."""
    response = requests.get(
        f"{OPENFGA_URL}/stores",
        headers=_get_auth_headers(),
        timeout=10,
    )
    if response.status_code == 200:
        stores = response.json().get("stores", [])
        for store in stores:
            if store.get("name") == EXPECTED_STORE_NAME:
                return store.get("id")
    return None


def _get_latest_model_id(store_id: str) -> str | None:
    """Get the latest authorization model ID for a store."""
    response = requests.get(
        f"{OPENFGA_URL}/stores/{store_id}/authorization-models",
        headers=_get_auth_headers(),
        timeout=10,
    )
    if response.status_code == 200:
        models = response.json().get("authorization_models", [])
        if models:
            return models[0].get("id")  # Latest model is first
    return None


@pytest.mark.xdist_group(name="test_openfga_seeding_flow")
class TestOpenFGASeedingStoreCreation:
    """Test that the seeding container creates the store correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_store_exists_after_seeding(self):
        """
        GIVEN: openfga-seed-test container has run
        WHEN: Listing stores via OpenFGA API
        THEN: Should find the agent-studio-openfga-store-test store

        User Journey: Developer runs make test-infra-up and store is auto-created
        """
        response = requests.get(
            f"{OPENFGA_URL}/stores",
            headers=_get_auth_headers(),
            timeout=10,
        )

        assert response.status_code == 200, f"Failed to list stores: {response.status_code}"

        stores = response.json().get("stores", [])
        store_names = [s.get("name") for s in stores]

        assert EXPECTED_STORE_NAME in store_names, (
            f"Expected store '{EXPECTED_STORE_NAME}' not found. Available stores: {store_names}"
        )

    def test_authorization_model_is_loaded(self):
        """
        GIVEN: Store exists after seeding
        WHEN: Listing authorization models
        THEN: Should have at least one model loaded

        User Journey: Authorization model from config/openfga/model.json is uploaded
        """
        store_id = _get_store_id()
        assert store_id is not None, f"Store '{EXPECTED_STORE_NAME}' not found"

        response = requests.get(
            f"{OPENFGA_URL}/stores/{store_id}/authorization-models",
            headers=_get_auth_headers(),
            timeout=10,
        )

        assert response.status_code == 200, f"Failed to list models: {response.status_code}"

        models = response.json().get("authorization_models", [])
        assert len(models) > 0, "No authorization models found - seeding may have failed"

        # Verify model has expected types
        latest_model = models[0]
        type_definitions = latest_model.get("type_definitions", [])
        type_names = [t.get("type") for t in type_definitions]

        expected_types = ["user", "organization", "tool", "conversation", "vector_store", "authz"]
        for expected in expected_types:
            assert expected in type_names, f"Expected type '{expected}' not in model. Found: {type_names}"


@pytest.mark.xdist_group(name="test_openfga_seeding_flow")
class TestOpenFGASeedingTupleVerification:
    """Test that relationship tuples are seeded correctly."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _check_permission(self, user: str, relation: str, obj: str) -> bool:
        """Check if user has permission via OpenFGA check endpoint."""
        store_id = _get_store_id()
        model_id = _get_latest_model_id(store_id)

        response = requests.post(
            f"{OPENFGA_URL}/stores/{store_id}/check",
            headers=_get_auth_headers(),
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

    def test_admin_has_owner_on_vector_store(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking if admin has owner permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Admin can manage vector store collections
        """
        allowed = self._check_permission("user:admin", "owner", "vector_store:default")
        assert allowed, "Admin should have owner permission on vector_store:default"

    def test_alice_has_viewer_on_vector_store(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking if alice has viewer permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Alice can view/search vector store
        """
        allowed = self._check_permission("user:alice", "viewer", "vector_store:default")
        assert allowed, "Alice should have viewer permission on vector_store:default"

    def test_bob_has_viewer_on_vector_store(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking if bob has viewer permission on vector_store:default
        THEN: Should return allowed=true

        User Journey: Bob can view/search vector store
        """
        allowed = self._check_permission("user:bob", "viewer", "vector_store:default")
        assert allowed, "Bob should have viewer permission on vector_store:default"

    # Note: authz:playground tests removed - playground deprecated
    # Removed: test_admin_has_admin_on_authz_playground
    # Removed: test_alice_has_viewer_on_authz_playground
    # Removed: test_bob_has_no_access_to_authz_playground


@pytest.mark.xdist_group(name="test_openfga_seeding_flow")
class TestOpenFGASeedingOrganizationPermissions:
    """Test organization-related permissions from seeding."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _check_permission(self, user: str, relation: str, obj: str) -> bool:
        """Check if user has permission via OpenFGA check endpoint."""
        store_id = _get_store_id()
        model_id = _get_latest_model_id(store_id)

        response = requests.post(
            f"{OPENFGA_URL}/stores/{store_id}/check",
            headers=_get_auth_headers(),
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

    def test_all_users_are_members_of_acme(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking organization membership
        THEN: admin, alice, and bob should all be members of organization:acme

        User Journey: All test users belong to the same organization
        """
        for user in ["user:admin", "user:alice", "user:bob"]:
            allowed = self._check_permission(user, "member", "organization:acme")
            assert allowed, f"{user} should be member of organization:acme"

    def test_alice_and_admin_are_org_admins(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking organization admin permissions
        THEN: admin and alice should be admins of organization:acme

        User Journey: Admin and Alice can manage organization settings
        """
        for user in ["user:admin", "user:alice"]:
            allowed = self._check_permission(user, "admin", "organization:acme")
            assert allowed, f"{user} should be admin of organization:acme"

    def test_bob_is_not_org_admin(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking if bob is org admin
        THEN: Should return allowed=false

        User Journey: Bob is a basic user without org admin privileges
        """
        allowed = self._check_permission("user:bob", "admin", "organization:acme")
        assert not allowed, "Bob should NOT be admin of organization:acme"


@pytest.mark.xdist_group(name="test_openfga_seeding_flow")
class TestOpenFGASeedingToolPermissions:
    """Test tool execution permissions from seeding."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _check_permission(self, user: str, relation: str, obj: str) -> bool:
        """Check if user has permission via OpenFGA check endpoint."""
        store_id = _get_store_id()
        model_id = _get_latest_model_id(store_id)

        response = requests.post(
            f"{OPENFGA_URL}/stores/{store_id}/check",
            headers=_get_auth_headers(),
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

    def test_all_users_can_execute_chat_tool(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking tool execution permissions
        THEN: All users should be able to execute tool:chat

        User Journey: All authenticated users can use the chat tool
        """
        for user in ["user:admin", "user:alice", "user:bob"]:
            allowed = self._check_permission(user, "executor", "tool:chat")
            assert allowed, f"{user} should be executor of tool:chat"


@pytest.mark.xdist_group(name="test_openfga_seeding_flow")
class TestOpenFGASeedingConversationPermissions:
    """Test conversation permissions from seeding."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _check_permission(self, user: str, relation: str, obj: str) -> bool:
        """Check if user has permission via OpenFGA check endpoint."""
        store_id = _get_store_id()
        model_id = _get_latest_model_id(store_id)

        response = requests.post(
            f"{OPENFGA_URL}/stores/{store_id}/check",
            headers=_get_auth_headers(),
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

    def test_alice_and_admin_own_thread_1(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking conversation ownership
        THEN: Alice and admin should own conversation:thread_1

        User Journey: Conversation creators have owner access
        """
        for user in ["user:alice", "user:admin"]:
            allowed = self._check_permission(user, "owner", "conversation:thread_1")
            assert allowed, f"{user} should be owner of conversation:thread_1"

    def test_bob_can_view_thread_1(self):
        """
        GIVEN: Seeding has completed
        WHEN: Checking if bob can view thread_1
        THEN: Should return allowed=true (bob has viewer access)

        User Journey: Bob was shared viewer access to the conversation
        """
        allowed = self._check_permission("user:bob", "viewer", "conversation:thread_1")
        assert allowed, "Bob should have viewer permission on conversation:thread_1"
