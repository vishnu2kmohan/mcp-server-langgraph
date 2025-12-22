"""
Unit tests for WebSocket Authorization Middleware.

Tests the WebSocketAuthorizationMiddleware class which implements
fine-grained authorization using OpenFGA ReBAC patterns.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.openfga,
    pytest.mark.xdist_group(name="websocket_authz"),
]


@pytest.mark.xdist_group(name="websocket_authz")
class TestWebSocketAuthorizationMiddleware:
    """Tests for WebSocketAuthorizationMiddleware class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_connection_allows_with_valid_permission(self) -> None:
        """GIVEN a user with valid permission WHEN checking connection THEN returns True."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("admin")

        assert result is True
        mock_client.check_permission.assert_called_once_with(
            user="user:admin",
            relation="admin",
            object="dashboard:alerts",
        )

    @pytest.mark.asyncio
    async def test_authorize_connection_denies_without_permission(self) -> None:
        """GIVEN a user without permission WHEN checking connection THEN returns False."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=False)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("bob")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_connection_uses_wildcard_for_none_resource_id(self) -> None:
        """GIVEN no resource_id WHEN checking connection THEN uses wildcard."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="mcp_connection",
            resource_id=None,  # No specific resource
            required_relation="viewer",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            await authz.authorize_connection("alice")

        mock_client.check_permission.assert_called_once_with(
            user="user:alice",
            relation="viewer",
            object="mcp_connection:*",
        )


@pytest.mark.xdist_group(name="websocket_authz")
class TestAuthorizationFailClosed:
    """Tests for fail-closed behavior on errors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fail_closed_denies_on_openfga_error(self) -> None:
        """GIVEN OpenFGA error WHEN fail_closed=True THEN denies access."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(side_effect=Exception("Connection refused"))

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
            fail_closed=True,  # Default, explicit for clarity
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("admin")

        assert result is False

    @pytest.mark.asyncio
    async def test_fail_closed_denies_when_openfga_unavailable(self) -> None:
        """GIVEN OpenFGA not configured WHEN fail_closed=True THEN denies access."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
            fail_closed=True,
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=None,  # OpenFGA not configured
        ):
            result = await authz.authorize_connection("admin")

        assert result is False

    @pytest.mark.asyncio
    async def test_fail_open_allows_on_openfga_error(self) -> None:
        """GIVEN OpenFGA error WHEN fail_closed=False THEN allows access."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(side_effect=Exception("Connection refused"))

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
            fail_closed=False,  # Fail-open mode
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("admin")

        assert result is True


@pytest.mark.xdist_group(name="websocket_authz")
class TestSubscriptionAuthorization:
    """Tests for authorize_subscription method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_subscription_checks_specific_resource(self) -> None:
        """GIVEN subscription request WHEN authorized THEN checks specific resource."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id=None,
            required_relation="executor",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_subscription("alice", "alice_workflow")

        assert result is True
        mock_client.check_permission.assert_called_once_with(
            user="user:alice",
            relation="executor",
            object="workflow:alice_workflow",
        )

    @pytest.mark.asyncio
    async def test_authorize_subscription_denies_other_users_resources(self) -> None:
        """GIVEN subscription to another user's resource WHEN not permitted THEN denies."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=False)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id=None,
            required_relation="executor",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_subscription("bob", "alice_workflow")

        assert result is False


@pytest.mark.xdist_group(name="websocket_authz")
class TestActionAuthorization:
    """Tests for authorize_action method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_action_uses_custom_relation(self) -> None:
        """GIVEN custom action relation WHEN checking THEN uses custom relation."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id=None,
            required_relation="viewer",  # Default relation
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            # Check for 'editor' action instead of default 'viewer'
            result = await authz.authorize_action("alice", "wf_123", action_relation="editor")

        assert result is True
        mock_client.check_permission.assert_called_once_with(
            user="user:alice",
            relation="editor",
            object="workflow:wf_123",
        )

    @pytest.mark.asyncio
    async def test_authorize_action_uses_default_relation_when_none(self) -> None:
        """GIVEN no custom action relation WHEN checking THEN uses default relation."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id=None,
            required_relation="viewer",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_action("bob", "wf_123")  # No action_relation

        assert result is True
        mock_client.check_permission.assert_called_once_with(
            user="user:bob",
            relation="viewer",  # Uses default
            object="workflow:wf_123",
        )


@pytest.mark.xdist_group(name="websocket_authz")
class TestSampleTuplesValidation:
    """
    Tests validating that sample tuples provide correct access.

    These tests verify the permission matrix defined in sample-tuples.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_admin_has_alert_websocket_access(self) -> None:
        """GIVEN admin user WHEN checking alerts access THEN allowed."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # Simulate what OpenFGA would return based on sample-tuples.json
        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("admin")

        assert result is True

    @pytest.mark.asyncio
    async def test_bob_lacks_alert_websocket_access(self) -> None:
        """GIVEN bob user WHEN checking alerts access THEN denied (not admin)."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # Based on sample-tuples.json, bob has no tuples for dashboard:alerts
        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=False)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("bob")

        assert result is False

    @pytest.mark.asyncio
    async def test_alice_has_audit_websocket_access(self) -> None:
        """GIVEN alice user WHEN checking audit logs access THEN allowed."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # alice has: viewer relation to logs:audit in sample-tuples.json
        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="logs",
            resource_id="audit",
            required_relation="viewer",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("alice")

        assert result is True

    @pytest.mark.asyncio
    async def test_all_users_have_notification_websocket_access(self) -> None:
        """GIVEN any user WHEN checking notification access THEN allowed."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # All users (admin, alice, bob) have viewer relation to chat:notifications
        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=True)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="chat",
            resource_id="notifications",
            required_relation="viewer",
        )

        for user in ["admin", "alice", "bob"]:
            with patch(
                "mcp_server_langgraph.websocket.authz.get_openfga_client",
                return_value=mock_client,
            ):
                result = await authz.authorize_connection(user)
                assert result is True, f"Expected {user} to have notification access"

    @pytest.mark.asyncio
    async def test_bob_lacks_hitl_websocket_access(self) -> None:
        """GIVEN bob user WHEN checking HITL access THEN denied (no editor relation)."""
        from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware

        # bob has no editor relation to workflow:hitl in sample-tuples.json
        mock_client = AsyncMock()
        mock_client.check_permission = AsyncMock(return_value=False)

        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id="hitl",
            required_relation="editor",
        )

        with patch(
            "mcp_server_langgraph.websocket.authz.get_openfga_client",
            return_value=mock_client,
        ):
            result = await authz.authorize_connection("bob")

        assert result is False
