"""
WebSocket Authorization Unit Tests (Mocked).

Unit tests for OpenFGA-based authorization on WebSocket endpoints.
Tests verify that personas (admin, alice, bob) have correct access to
WebSocket endpoints based on the authorization tuples in sample-tuples.json.

Note: These tests use MOCKS for OpenFGA and should be considered unit tests.
TODO: Move to tests/unit/websocket/ in a future refactor.
Real integration tests using actual OpenFGA infrastructure are in:
- tests/integration/test_openfga_real_infrastructure.py

Architecture:
- Uses mock OpenFGA client to simulate authorization checks
- Tests all WebSocket endpoints with different personas
- Verifies authorization denial for unauthorized access

Reference: config/openfga/sample-tuples.json for authorization mappings
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from mcp_server_langgraph.websocket.authz import WebSocketAuthorizationMiddleware
from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig
from tests.conftest import get_user_id

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.openfga,
    pytest.mark.asyncio,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-websocket-auth"


# =============================================================================
# Test Personas (matching sample-tuples.json)
# =============================================================================

PERSONAS = {
    "admin": {
        "user_id": get_user_id("admin"),
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin", "user"],
    },
    "alice": {
        "user_id": get_user_id("alice"),
        "username": "alice",
        "email": "alice@example.com",
        "roles": ["editor", "user"],
    },
    "bob": {
        "user_id": get_user_id("bob"),
        "username": "bob",
        "email": "bob@example.com",
        "roles": ["user"],
    },
}


def _create_test_jwt(persona: str, expires_in: int = 3600) -> str:
    """Create a test JWT token for a specific persona."""
    p = PERSONAS[persona]
    now = datetime.now(UTC)
    payload = {
        "sub": p["user_id"],
        "username": p["username"],
        "email": p["email"],
        "roles": p["roles"],
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "jti": f"{p['username']}_{int(now.timestamp() * 1000)}",
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


# =============================================================================
# Authorization Test Handler
# =============================================================================


class AuthorizedWebSocketHandler(WebSocketBase):
    """Test WebSocket handler with OpenFGA authorization."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        required_relation: str,
    ):
        config = WebSocketConfig(
            endpoint_name=f"authz-{resource_type}",
            require_auth=True,
            authz_resource_type=resource_type,
            authz_resource_id=resource_id,
            authz_required_relation=required_relation,
            authz_fail_closed=True,
        )
        super().__init__(config)

    async def on_connect(self, user) -> None:
        pass

    async def on_disconnect(self) -> None:
        pass

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        return MessageEnvelope(type="authorized", payload={"status": "ok"})


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_jwt_validator():
    """Mock JWT validation to accept test tokens."""
    with patch("mcp_server_langgraph.websocket.middleware.AuthMiddleware") as mock_auth:
        mock_instance = MagicMock()

        async def mock_validate(token: str):
            # Decode the token to get user info
            try:
                payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
                return MagicMock(
                    id=payload["sub"],
                    username=payload["username"],
                    email=payload["email"],
                    roles=payload.get("roles", []),
                )
            except jwt.InvalidTokenError:
                return None

        mock_instance.validate_token = mock_validate
        mock_auth.return_value = mock_instance
        yield mock_auth


@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for authorization checks."""
    with patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_get:
        mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config - configured below

        # Define authorization rules matching sample-tuples.json
        # Note: parameter name must be 'object' to match authz.py keyword argument
        async def check_permission(
            user: str,
            relation: str,
            object: str,
        ) -> bool:
            """Simulate OpenFGA authorization check based on sample tuples."""
            # Extract user_id from "user:xxx" format
            user_id = user.replace("user:", "") if user.startswith("user:") else user

            # Authorization mapping based on sample-tuples.json
            auth_rules = {
                # Alert WebSocket - admin only
                ("admin", "admin", "dashboard:alerts"): True,
                ("alice", "admin", "dashboard:alerts"): False,
                ("bob", "admin", "dashboard:alerts"): False,
                # Audit WebSocket - admin (admin), alice (viewer)
                ("admin", "admin", "logs:audit"): True,
                ("admin", "viewer", "logs:audit"): True,
                ("alice", "viewer", "logs:audit"): True,
                ("alice", "admin", "logs:audit"): False,
                ("bob", "viewer", "logs:audit"): False,
                ("bob", "admin", "logs:audit"): False,
                # Notification WebSocket - all users (viewer)
                ("admin", "viewer", "chat:notifications"): True,
                ("alice", "viewer", "chat:notifications"): True,
                ("bob", "viewer", "chat:notifications"): True,
                # HITL WebSocket - editors only
                ("admin", "editor", "workflow:hitl"): True,
                ("alice", "editor", "workflow:hitl"): True,
                ("bob", "editor", "workflow:hitl"): False,
                # MCP WebSocket - all authenticated users
                ("admin", "user", "mcp:websocket"): True,
                ("alice", "user", "mcp:websocket"): True,
                ("bob", "user", "mcp:websocket"): True,
                # Connection Health WebSocket - all viewers
                ("admin", "viewer", "mcp_connection:health"): True,
                ("alice", "viewer", "mcp_connection:health"): True,
                ("bob", "viewer", "mcp_connection:health"): True,
                # HEART Metrics WebSocket - all viewers
                ("admin", "viewer", "observability:heart"): True,
                ("alice", "viewer", "observability:heart"): True,
                ("bob", "viewer", "observability:heart"): True,
                # Cost Tracking WebSocket - all viewers
                ("admin", "viewer", "cost:usage"): True,
                ("alice", "viewer", "cost:usage"): True,
                ("bob", "viewer", "cost:usage"): True,
            }
            return auth_rules.get((user_id, relation, object), False)

        mock_client.check_permission = check_permission
        mock_get.return_value = mock_client
        yield mock_client


# =============================================================================
# Unit Tests for WebSocketAuthorizationMiddleware
# =============================================================================


@pytest.mark.xdist_group(name="websocket_auth")
class TestWebSocketAuthorizationMiddleware:
    """Unit tests for authorization middleware."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_admin_can_access_alert_stream(self, mock_openfga_client):
        """GIVEN admin user WHEN accessing dashboard:alerts THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )
        result = await authz.authorize_connection("admin")
        assert result is True

    async def test_alice_cannot_access_alert_stream(self, mock_openfga_client):
        """GIVEN alice user WHEN accessing dashboard:alerts THEN denied."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )
        result = await authz.authorize_connection("alice")
        assert result is False

    async def test_bob_cannot_access_alert_stream(self, mock_openfga_client):
        """GIVEN bob user WHEN accessing dashboard:alerts THEN denied."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="dashboard",
            resource_id="alerts",
            required_relation="admin",
        )
        result = await authz.authorize_connection("bob")
        assert result is False

    async def test_admin_can_access_audit_stream(self, mock_openfga_client):
        """GIVEN admin user WHEN accessing logs:audit THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="logs",
            resource_id="audit",
            required_relation="viewer",
        )
        result = await authz.authorize_connection("admin")
        assert result is True

    async def test_alice_can_access_audit_stream_as_viewer(self, mock_openfga_client):
        """GIVEN alice user WHEN accessing logs:audit as viewer THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="logs",
            resource_id="audit",
            required_relation="viewer",
        )
        result = await authz.authorize_connection("alice")
        assert result is True

    async def test_bob_cannot_access_audit_stream(self, mock_openfga_client):
        """GIVEN bob user WHEN accessing logs:audit THEN denied."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="logs",
            resource_id="audit",
            required_relation="viewer",
        )
        result = await authz.authorize_connection("bob")
        assert result is False

    async def test_all_users_can_access_notifications(self, mock_openfga_client):
        """GIVEN any user WHEN accessing chat:notifications THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="chat",
            resource_id="notifications",
            required_relation="viewer",
        )
        for persona in ["admin", "alice", "bob"]:
            result = await authz.authorize_connection(persona)
            assert result is True, f"{persona} should access notifications"

    async def test_editors_can_access_hitl_stream(self, mock_openfga_client):
        """GIVEN editor user WHEN accessing workflow:hitl THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id="hitl",
            required_relation="editor",
        )
        # admin and alice are editors
        assert await authz.authorize_connection("admin") is True
        assert await authz.authorize_connection("alice") is True

    async def test_bob_cannot_access_hitl_stream(self, mock_openfga_client):
        """GIVEN bob (non-editor) WHEN accessing workflow:hitl THEN denied."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="workflow",
            resource_id="hitl",
            required_relation="editor",
        )
        result = await authz.authorize_connection("bob")
        assert result is False

    async def test_all_users_can_access_mcp_websocket(self, mock_openfga_client):
        """GIVEN any authenticated user WHEN accessing mcp:websocket THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="mcp",
            resource_id="websocket",
            required_relation="user",
        )
        for persona in ["admin", "alice", "bob"]:
            result = await authz.authorize_connection(persona)
            assert result is True, f"{persona} should access MCP WebSocket"

    async def test_all_users_can_access_connection_health(self, mock_openfga_client):
        """GIVEN any user WHEN accessing mcp_connection:health THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="mcp_connection",
            resource_id="health",
            required_relation="viewer",
        )
        for persona in ["admin", "alice", "bob"]:
            result = await authz.authorize_connection(persona)
            assert result is True, f"{persona} should access connection health"

    async def test_all_users_can_access_heart_metrics(self, mock_openfga_client):
        """GIVEN any user WHEN accessing observability:heart THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="observability",
            resource_id="heart",
            required_relation="viewer",
        )
        for persona in ["admin", "alice", "bob"]:
            result = await authz.authorize_connection(persona)
            assert result is True, f"{persona} should access HEART metrics"

    async def test_all_users_can_access_cost_tracking(self, mock_openfga_client):
        """GIVEN any user WHEN accessing cost:usage THEN authorized."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type="cost",
            resource_id="usage",
            required_relation="viewer",
        )
        for persona in ["admin", "alice", "bob"]:
            result = await authz.authorize_connection(persona)
            assert result is True, f"{persona} should access cost tracking"


# =============================================================================
# Authorization Fail-Closed Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_auth_failclosed")
class TestAuthorizationFailClosed:
    """Test fail-closed behavior on authorization errors."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_fail_closed_on_openfga_error(self):
        """GIVEN OpenFGA unavailable WHEN checking auth THEN deny access."""
        with patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_get:
            mock_client = AsyncMock(return_value=None)
            mock_client.check_permission.side_effect = Exception("Connection refused")
            mock_get.return_value = mock_client

            authz = WebSocketAuthorizationMiddleware(
                resource_type="dashboard",
                resource_id="alerts",
                required_relation="admin",
                fail_closed=True,
            )
            result = await authz.authorize_connection("admin")
            assert result is False

    async def test_fail_open_when_configured(self):
        """GIVEN fail_closed=False WHEN OpenFGA unavailable THEN allow access."""
        with patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_get:
            mock_client = AsyncMock(return_value=None)
            mock_client.check_permission.side_effect = Exception("Connection refused")
            mock_get.return_value = mock_client

            authz = WebSocketAuthorizationMiddleware(
                resource_type="dashboard",
                resource_id="alerts",
                required_relation="admin",
                fail_closed=False,
            )
            result = await authz.authorize_connection("admin")
            assert result is True

    async def test_fail_closed_when_openfga_returns_none(self):
        """GIVEN get_openfga_client returns None WHEN fail_closed=True THEN deny."""
        with patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_get:
            mock_get.return_value = None

            authz = WebSocketAuthorizationMiddleware(
                resource_type="dashboard",
                resource_id="alerts",
                required_relation="admin",
                fail_closed=True,
            )
            result = await authz.authorize_connection("admin")
            assert result is False

    async def test_fail_open_when_openfga_returns_none(self):
        """GIVEN get_openfga_client returns None WHEN fail_closed=False THEN allow."""
        with patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_get:
            mock_get.return_value = None

            authz = WebSocketAuthorizationMiddleware(
                resource_type="dashboard",
                resource_id="alerts",
                required_relation="admin",
                fail_closed=False,
            )
            result = await authz.authorize_connection("admin")
            assert result is True


# =============================================================================
# Authorization Matrix Tests (All Endpoints x All Personas)
# =============================================================================


@pytest.mark.xdist_group(name="websocket_auth_matrix")
class TestAuthorizationMatrix:
    """Comprehensive authorization matrix tests for all endpoints and personas."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "endpoint,resource_type,resource_id,relation,admin_allowed,alice_allowed,bob_allowed",
        [
            # Alert WebSocket - admin only
            ("alerts", "dashboard", "alerts", "admin", True, False, False),
            # Audit WebSocket - admin and alice
            ("audit", "logs", "audit", "viewer", True, True, False),
            # Notification WebSocket - all users
            ("notifications", "chat", "notifications", "viewer", True, True, True),
            # HITL WebSocket - editors only
            ("hitl", "workflow", "hitl", "editor", True, True, False),
            # MCP WebSocket - all authenticated users
            ("mcp", "mcp", "websocket", "user", True, True, True),
            # Connection Health - all viewers
            ("connections", "mcp_connection", "health", "viewer", True, True, True),
            # HEART Metrics - all viewers
            ("heart", "observability", "heart", "viewer", True, True, True),
            # Cost Tracking - all viewers
            ("cost", "cost", "usage", "viewer", True, True, True),
        ],
    )
    async def test_endpoint_authorization_matrix(
        self,
        mock_openfga_client,
        endpoint: str,
        resource_type: str,
        resource_id: str,
        relation: str,
        admin_allowed: bool,
        alice_allowed: bool,
        bob_allowed: bool,
    ):
        """Test authorization for all endpoints with all personas."""
        authz = WebSocketAuthorizationMiddleware(
            resource_type=resource_type,
            resource_id=resource_id,
            required_relation=relation,
        )

        admin_result = await authz.authorize_connection("admin")
        alice_result = await authz.authorize_connection("alice")
        bob_result = await authz.authorize_connection("bob")

        assert admin_result == admin_allowed, f"admin access to {endpoint}: expected {admin_allowed}, got {admin_result}"
        assert alice_result == alice_allowed, f"alice access to {endpoint}: expected {alice_allowed}, got {alice_result}"
        assert bob_result == bob_allowed, f"bob access to {endpoint}: expected {bob_allowed}, got {bob_result}"
