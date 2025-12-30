"""
Integration tests for Chat API Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Chat resources (/api/v1/chat)
2. Chat ownership and viewing

RED PHASE: These tests use EXISTING tuples but verify API endpoints
will enforce authorization (currently missing).

User Journeys:
- Admin: owner of chat:admin_chat (full CRUD)
- Alice: owner of chat:alice_chat (full CRUD on own)
- Bob: owner of chat:bob_chat (full CRUD on own)

Reference: Plan - Phase 5.3: Chat API
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
    pytest.mark.chat,
]


# URLs and credentials
OPENFGA_URL = os.getenv("OPENFGA_URL", "http://localhost:9080")
OPENFGA_PRESHARED_KEY = os.getenv("OPENFGA_PRESHARED_KEY", "test-openfga-preshared-key")


def _get_openfga_store_and_model() -> tuple[str | None, str | None]:
    """Dynamically discover OpenFGA store and model IDs."""
    headers = {
        "Authorization": f"Bearer {OPENFGA_PRESHARED_KEY}",
        "Content-Type": "application/json",
    }

    try:
        stores_resp = requests.get(f"{OPENFGA_URL}/stores", headers=headers, timeout=10)
        if stores_resp.status_code != 200:
            return None, None

        stores = stores_resp.json().get("stores", [])
        store_id = None
        for store in stores:
            if store.get("name") == "mcp-server-langgraph-test":
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

    headers = {
        "Authorization": f"Bearer {OPENFGA_PRESHARED_KEY}",
        "Content-Type": "application/json",
    }

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


@pytest.mark.xdist_group(name="test_chat_authorization")
class TestChatOwnership:
    """
    Test chat ownership authorization from sample-tuples.json.

    Each user owns their own chat resources.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_owns_admin_chat(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner chat:admin_chat
        WHEN: Checking admin's owner permission
        THEN: Should return allowed=true

        User Journey: Admin can manage their chat sessions
        API Endpoint: DELETE /api/v1/chat/{id}
        """
        allowed = _check_permission("user:admin", "owner", "chat:admin_chat")
        assert allowed, "Admin should be owner of chat:admin_chat"

    def test_alice_owns_alice_chat(self):
        """
        GIVEN: Pre-seeded tuple user:alice owner chat:alice_chat
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=true

        User Journey: Alice can manage her chat sessions
        API Endpoint: PUT /api/v1/chat/{id}
        """
        allowed = _check_permission("user:alice", "owner", "chat:alice_chat")
        assert allowed, "Alice should be owner of chat:alice_chat"

    def test_bob_owns_bob_chat(self):
        """
        GIVEN: Pre-seeded tuple user:bob owner chat:bob_chat
        WHEN: Checking bob's owner permission
        THEN: Should return allowed=true

        User Journey: Bob can manage his chat sessions
        """
        allowed = _check_permission("user:bob", "owner", "chat:bob_chat")
        assert allowed, "Bob should be owner of chat:bob_chat"


@pytest.mark.xdist_group(name="test_chat_authorization")
class TestChatIsolation:
    """
    Test that users cannot access other users' chat sessions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_cannot_own_admin_chat(self):
        """
        GIVEN: Alice has no tuple for chat:admin_chat
        WHEN: Checking alice's owner permission on admin's chat
        THEN: Should return allowed=false

        User Journey: Users cannot manage other users' chats
        """
        allowed = _check_permission("user:alice", "owner", "chat:admin_chat")
        assert not allowed, "Alice should NOT be able to own admin's chat"

    def test_bob_cannot_own_alice_chat(self):
        """
        GIVEN: Bob has no tuple for chat:alice_chat
        WHEN: Checking bob's owner permission on alice's chat
        THEN: Should return allowed=false

        User Journey: Chat sessions are private to their owners
        """
        allowed = _check_permission("user:bob", "owner", "chat:alice_chat")
        assert not allowed, "Bob should NOT be able to own alice's chat"

    def test_bob_cannot_view_alice_chat(self):
        """
        GIVEN: Bob has no viewer tuple for chat:alice_chat
        WHEN: Checking bob's viewer permission on alice's chat
        THEN: Should return allowed=false

        User Journey: Chat sessions are not viewable by others
        API Endpoint: GET /api/v1/chat/{id} should fail for bob on alice's chat
        """
        allowed = _check_permission("user:bob", "viewer", "chat:alice_chat")
        assert not allowed, "Bob should NOT be able to view alice's chat"


@pytest.mark.xdist_group(name="test_chat_authorization")
class TestChatViewerAccess:
    """
    Test chat viewer authorization.

    Owners should automatically have viewer access via inheritance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_view_own_chat(self):
        """
        GIVEN: Admin is owner of chat:admin_chat
        WHEN: Checking admin's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Owners can always view their chats
        """
        allowed = _check_permission("user:admin", "viewer", "chat:admin_chat")
        assert allowed, "Admin should be viewer (via owner inheritance) of chat:admin_chat"

    def test_alice_can_view_own_chat(self):
        """
        GIVEN: Alice is owner of chat:alice_chat
        WHEN: Checking alice's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Alice can view her chats
        API Endpoint: GET /api/v1/chat/{id}
        """
        allowed = _check_permission("user:alice", "viewer", "chat:alice_chat")
        assert allowed, "Alice should be viewer (via owner inheritance) of chat:alice_chat"

    def test_bob_can_view_own_chat(self):
        """
        GIVEN: Bob is owner of chat:bob_chat
        WHEN: Checking bob's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Bob can view his chats
        """
        allowed = _check_permission("user:bob", "viewer", "chat:bob_chat")
        assert allowed, "Bob should be viewer (via owner inheritance) of chat:bob_chat"


@pytest.mark.xdist_group(name="test_chat_authorization")
class TestChatNotificationsAccess:
    """
    Test chat notifications access for WebSocket endpoint.

    All authenticated users should be able to receive notifications.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_view_notifications(self):
        """
        GIVEN: Pre-seeded tuple user:admin viewer chat:notifications
        WHEN: Checking admin's viewer permission on notifications
        THEN: Should return allowed=true

        User Journey: Admin can receive notifications
        WebSocket: /api/v1/ws/notifications
        """
        allowed = _check_permission("user:admin", "viewer", "chat:notifications")
        assert allowed, "Admin should have viewer access to chat:notifications"

    def test_alice_can_view_notifications(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer chat:notifications
        WHEN: Checking alice's viewer permission on notifications
        THEN: Should return allowed=true

        User Journey: Alice can receive notifications
        WebSocket: /api/v1/ws/notifications
        """
        allowed = _check_permission("user:alice", "viewer", "chat:notifications")
        assert allowed, "Alice should have viewer access to chat:notifications"

    def test_bob_can_view_notifications(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer chat:notifications
        WHEN: Checking bob's viewer permission on notifications
        THEN: Should return allowed=true

        User Journey: Bob can receive notifications
        WebSocket: /api/v1/ws/notifications
        """
        allowed = _check_permission("user:bob", "viewer", "chat:notifications")
        assert allowed, "Bob should have viewer access to chat:notifications"
