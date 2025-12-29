"""
Integration tests for OpenFGA using REAL infrastructure.

These tests connect to the actual OpenFGA server from docker-compose.test.yml
and verify that the authorization system works end-to-end.

NO MOCKS are used for OpenFGA in these tests. This ensures we catch bugs like
the missing set_global_openfga_client() call that mocked tests missed.

Prerequisites:
    docker compose -f docker-compose.test.yml up -d

Related issues fixed:
    - WebSocket authorization failed because get_openfga_client() returned None
    - set_global_openfga_client() was never called in server_streamable.py lifespan
    - All tests mocked get_openfga_client() so never caught the initialization bug
"""

import gc
import os

import pytest

pytestmark = pytest.mark.integration

# Note: skip_if_openfga_unavailable fixture is defined in tests/integration/conftest.py


@pytest.mark.integration
@pytest.mark.xdist_group(name="openfga_real")
class TestOpenFGARealInfrastructure:
    """Tests using REAL OpenFGA from docker-compose.test.yml - NO MOCKS."""

    def teardown_method(self) -> None:
        """Force GC and clear global state."""
        # Clear global OpenFGA client between tests
        from mcp_server_langgraph.auth.openfga import clear_global_openfga_client

        clear_global_openfga_client()
        gc.collect()

    @pytest.mark.asyncio
    async def test_openfga_client_connects_to_real_server(self, openfga_client_real) -> None:
        """
        GIVEN: Real OpenFGA server from docker-compose.test.yml
        WHEN: OpenFGAClient is initialized
        THEN: It can connect and has valid store_id and model_id
        """
        # THEN: Client has valid configuration
        assert openfga_client_real.store_id is not None, "store_id should be set"
        assert openfga_client_real.model_id is not None, "model_id should be set"
        assert openfga_client_real.api_url is not None, "api_url should be set"

    @pytest.mark.asyncio
    async def test_set_global_openfga_client_makes_client_available(self, openfga_client_real) -> None:
        """
        GIVEN: Real OpenFGA client
        WHEN: set_global_openfga_client() is called
        THEN: get_openfga_client() returns the same client

        This tests the exact pattern used by server_streamable.py lifespan.
        """
        from mcp_server_langgraph.auth.openfga import (
            get_openfga_client,
            set_global_openfga_client,
        )

        # GIVEN: No global client set initially
        # Note: teardown clears it, so we start clean

        # WHEN: Set global client
        set_global_openfga_client(openfga_client_real)

        # THEN: get_openfga_client returns the same client
        retrieved_client = await get_openfga_client()
        assert retrieved_client is openfga_client_real
        assert retrieved_client.store_id == openfga_client_real.store_id

    @pytest.mark.asyncio
    async def test_websocket_authz_middleware_works_with_real_openfga(self, openfga_client_real) -> None:
        """
        GIVEN: Real OpenFGA client set as global
        WHEN: WebSocketAuthorizationMiddleware.authorize_connection() is called
        THEN: It uses the real client to check permissions

        This is the exact bug scenario - before the fix, get_openfga_client()
        returned None because set_global_openfga_client() was never called.
        """
        from mcp_server_langgraph.auth.openfga import set_global_openfga_client
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # GIVEN: Set real OpenFGA client as global (simulates lifespan startup)
        set_global_openfga_client(openfga_client_real)

        # GIVEN: Authorization middleware for chat notifications
        authz = WebSocketAuthorizationMiddleware(
            resource_type="chat",
            resource_id="notifications",
            required_relation="viewer",
            fail_closed=True,
        )

        # WHEN: Authorize connection for alice (who has viewer relation in sample tuples)
        # Note: alice is seeded with permissions in config/openfga/sample-tuples.json
        result = await authz.authorize_connection("user:alice")

        # THEN: Authorization should succeed (alice has permissions)
        # If OpenFGA wasn't properly initialized, this would return False
        assert result is True, (
            "Authorization should succeed for alice. If this fails, check that sample-tuples.json is seeded correctly."
        )

    @pytest.mark.asyncio
    async def test_websocket_authz_denies_unauthorized_user(self, openfga_client_real) -> None:
        """
        GIVEN: Real OpenFGA client set as global
        WHEN: authorize_connection() is called for a user WITHOUT permissions
        THEN: Authorization is denied

        This verifies that permissions are actually checked, not just granted.
        """
        from mcp_server_langgraph.auth.openfga import set_global_openfga_client
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # GIVEN: Set real OpenFGA client as global
        set_global_openfga_client(openfga_client_real)

        # GIVEN: Authorization middleware for a resource
        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id="secret-workflow-12345",  # Non-existent workflow
            required_relation="owner",
            fail_closed=True,
        )

        # WHEN: Authorize connection for unknown user (not in tuples)
        result = await authz.authorize_connection("user:unknown-user-xyz")

        # THEN: Authorization should fail (no tuple for this user)
        assert result is False, "Authorization should fail for unknown user without permissions."

    @pytest.mark.asyncio
    async def test_global_client_clear_prevents_authorization(self, openfga_client_real) -> None:
        """
        GIVEN: Real OpenFGA client was set as global
        WHEN: clear_global_openfga_client() is called (simulates shutdown)
        THEN: get_openfga_client() returns None and authz fails with fail_closed=True

        This verifies the cleanup path in server_streamable.py lifespan.
        """
        from mcp_server_langgraph.auth.openfga import (
            clear_global_openfga_client,
            get_openfga_client,
            set_global_openfga_client,
        )
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # GIVEN: Set and then clear global client
        set_global_openfga_client(openfga_client_real)
        clear_global_openfga_client()

        # THEN: get_openfga_client returns None
        assert await get_openfga_client() is None

        # AND: Authorization fails with fail_closed=True
        authz = WebSocketAuthorizationMiddleware(
            resource_type="chat",
            resource_id="notifications",
            required_relation="viewer",
            fail_closed=True,
        )
        result = await authz.authorize_connection("user:alice")
        assert result is False, "Authorization should fail when global client is cleared."


@pytest.mark.integration
@pytest.mark.xdist_group(name="openfga_real")
class TestOpenFGAPermissionChecks:
    """Test actual permission checks against real OpenFGA with seeded tuples."""

    def teardown_method(self) -> None:
        """Force GC and clear global state."""
        from mcp_server_langgraph.auth.openfga import clear_global_openfga_client

        clear_global_openfga_client()
        gc.collect()

    @pytest.mark.asyncio
    async def test_alice_has_chat_executor_permission(self, openfga_client_real) -> None:
        """
        GIVEN: Alice is seeded with executor relation on tool:chat
        WHEN: check_permission is called
        THEN: Permission is granted

        Verifies: config/openfga/sample-tuples.json tuple:
            {"user": "user:alice", "relation": "executor", "object": "tool:chat"}
        """
        # Check direct permission
        result = await openfga_client_real.check_permission(
            user="user:alice",
            relation="executor",
            object_type="tool",
            object_id="chat",
        )
        assert result is True, (
            "Alice should have executor permission on tool:chat. Check that sample-tuples.json is seeded correctly."
        )

    @pytest.mark.asyncio
    async def test_alice_has_admin_status(self, openfga_client_real) -> None:
        """
        GIVEN: Alice is seeded with admin relation on system:default
        WHEN: check_permission is called
        THEN: Permission is granted

        Verifies: config/openfga/sample-tuples.json tuple:
            {"user": "user:alice", "relation": "admin", "object": "system:default"}
        """
        result = await openfga_client_real.check_permission(
            user="user:alice",
            relation="admin",
            object_type="system",
            object_id="default",
        )
        assert result is True, "Alice should have admin status. Check that sample-tuples.json is seeded correctly."

    @pytest.mark.asyncio
    async def test_bob_is_member_but_not_admin(self, openfga_client_real) -> None:
        """
        GIVEN: Bob is seeded with member but NOT admin relation
        WHEN: check_permission is called for admin
        THEN: Permission is denied

        Verifies: Bob has member but lacks admin in sample-tuples.json
        """
        # Bob should be a member
        member_result = await openfga_client_real.check_permission(
            user="user:bob",
            relation="member",
            object_type="organization",
            object_id="default",
        )
        assert member_result is True, "Bob should be a member of organization:default"

        # Bob should NOT be an admin
        admin_result = await openfga_client_real.check_permission(
            user="user:bob",
            relation="admin",
            object_type="system",
            object_id="default",
        )
        assert admin_result is False, "Bob should NOT have admin status"

    @pytest.mark.asyncio
    async def test_workflow_ownership_permissions(self, openfga_client_real) -> None:
        """
        GIVEN: Alice owns workflow:test-workflow-1 (seeded tuple)
        WHEN: check_permission is called for owner
        THEN: Permission is granted for alice, denied for bob

        Verifies cross-user access control from sample-tuples.json:
            {"user": "user:alice", "relation": "owner", "object": "workflow:test-workflow-1"}
            {"user": "user:bob", "relation": "viewer", "object": "workflow:test-workflow-1"}
        """
        # Alice is owner
        alice_owner = await openfga_client_real.check_permission(
            user="user:alice",
            relation="owner",
            object_type="workflow",
            object_id="test-workflow-1",
        )
        assert alice_owner is True, "Alice should own workflow:test-workflow-1"

        # Bob is viewer, not owner
        bob_owner = await openfga_client_real.check_permission(
            user="user:bob",
            relation="owner",
            object_type="workflow",
            object_id="test-workflow-1",
        )
        assert bob_owner is False, "Bob should NOT own workflow:test-workflow-1"

        bob_viewer = await openfga_client_real.check_permission(
            user="user:bob",
            relation="viewer",
            object_type="workflow",
            object_id="test-workflow-1",
        )
        assert bob_viewer is True, "Bob should be viewer of workflow:test-workflow-1"


@pytest.mark.integration
@pytest.mark.xdist_group(name="openfga_real")
class TestBootstrapSecurityRealIntegration:
    """Test bootstrap/security.py init_auth() with real OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC and clear global state."""
        from mcp_server_langgraph.auth.openfga import clear_global_openfga_client

        clear_global_openfga_client()
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_auth_sets_real_global_client(self, test_infrastructure_ports) -> None:
        """
        GIVEN: Real OpenFGA server available
        WHEN: init_auth() is called with real settings
        THEN: set_global_openfga_client() is called with a working client

        This tests the ACTUAL initialization path, not mocked.
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.auth.openfga import (
            get_openfga_client,
            clear_global_openfga_client,
        )
        from mcp_server_langgraph.bootstrap.security import init_auth

        # Create real settings pointing to test infrastructure
        settings = MagicMock()
        settings.openfga_store_id = os.getenv("OPENFGA_STORE_ID")
        settings.openfga_store_name = None
        settings.openfga_model_id = os.getenv("OPENFGA_MODEL_ID")
        settings.openfga_api_url = f"http://localhost:{test_infrastructure_ports['openfga_http']}"
        settings.openfga_oidc_client_id = None
        settings.openfga_oidc_client_secret = None
        settings.openfga_oidc_issuer = None
        settings.openfga_preshared_key = os.getenv("OPENFGA_PRESHARED_KEY", "test-openfga-preshared-key")
        settings.jwt_secret_key = "test-secret-key"
        settings.auth_provider = "inmemory"
        settings.keycloak_server_url = "http://localhost:9082"
        settings.keycloak_realm = "default"

        # Skip if store not initialized
        if not settings.openfga_store_id:
            pytest.skip("OpenFGA store not initialized. Run: docker compose -f docker-compose.test.yml up -d")

        try:
            # WHEN: init_auth is called
            security_state = await init_auth(settings)

            # THEN: Global client is set and working
            global_client = await get_openfga_client()
            assert global_client is not None, (
                "Global OpenFGA client should be set after init_auth(). "
                "This is the bug we fixed: set_global_openfga_client() wasn't called."
            )

            # AND: Client has correct configuration
            assert global_client.store_id == settings.openfga_store_id
            assert global_client.api_url == settings.openfga_api_url

            # AND: SecurityState contains the client
            assert security_state.openfga_client is not None

        finally:
            # Cleanup
            if security_state and security_state.openfga_client:
                await security_state.cleanup()
            clear_global_openfga_client()
