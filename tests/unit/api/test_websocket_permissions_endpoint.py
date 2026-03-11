"""
Unit tests for WebSocket permissions in GET /api/v1/me endpoint.

Tests verify that the /api/v1/me endpoint correctly returns websocket_permissions
via OpenFGA batch check. This is critical for frontend WebSocket hooks that check
permissions before attempting to connect.

Reference: GitHub issue - StatusBar shows "Disconnected" after OAuth login
Fix: AuthCallbackPage now calls initializeAuth() which fetches /api/v1/me
     including websocket_permissions for frontend hook permission checks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.user import user_router, WebSocketPermissions

# Module-level pytest marker
pytestmark = pytest.mark.unit


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_admin_user() -> dict[str, Any]:
    """Mock authenticated admin user."""
    return {
        "user_id": "user:admin",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin"],
        "persona": "admin",
        "sub_persona": None,
    }


@pytest.fixture
def mock_alice_user() -> dict[str, Any]:
    """Mock authenticated developer user (alice)."""
    return {
        "user_id": "user:alice",
        "username": "alice",
        "email": "alice@example.com",
        "roles": ["developer"],
        "persona": "developer",
        "sub_persona": None,
    }


@pytest.fixture
def mock_bob_user() -> dict[str, Any]:
    """Mock authenticated basic user (bob)."""
    return {
        "user_id": "user:bob",
        "username": "bob",
        "email": "bob@example.com",
        "roles": ["user"],
        "persona": "user",
        "sub_persona": None,
    }


def create_app_with_user(user: dict[str, Any]) -> FastAPI:
    """Create test FastAPI app with user_router and mocked auth."""
    from mcp_server_langgraph.auth.middleware import get_current_user

    test_app = FastAPI()

    # Override auth dependency
    async def override_get_current_user() -> dict[str, Any]:
        return user

    test_app.dependency_overrides[get_current_user] = override_get_current_user
    test_app.include_router(user_router, prefix="/api/v1")

    return test_app


def create_admin_permissions() -> WebSocketPermissions:
    """Create permissions for admin user - all True (17/17)."""
    return WebSocketPermissions(
        alerts=True,
        notifications=True,
        devtools=True,
        audit=True,
        mcp_tasks=True,
        mcp_aggregated=True,
        connections_health=True,
        connections_realtime=True,
        heart_metrics=True,
        traces=True,
        cost_tracking=True,
        budget_alerts=True,
        agent_requests=True,
        ai_suggestions=True,
        orchestrator_status=True,
        llm_streaming=True,
        session_metrics=True,
    )


def create_developer_permissions() -> WebSocketPermissions:
    """Create permissions for developer user (alice) - alerts=False (16/17)."""
    return WebSocketPermissions(
        alerts=False,  # Admin only
        notifications=True,
        devtools=True,
        audit=True,
        mcp_tasks=True,
        mcp_aggregated=True,
        connections_health=True,
        connections_realtime=True,
        heart_metrics=True,
        traces=True,
        cost_tracking=True,
        budget_alerts=True,
        agent_requests=True,  # Editor on workflow:hitl
        ai_suggestions=True,
        orchestrator_status=True,
        llm_streaming=True,
        session_metrics=True,
    )


def create_basic_user_permissions() -> WebSocketPermissions:
    """Create permissions for basic user (bob) - minimal permissions (15/17)."""
    return WebSocketPermissions(
        alerts=False,  # Admin only
        notifications=True,
        devtools=True,  # All users can view devtools
        audit=True,  # All users can view audit logs
        mcp_tasks=True,
        mcp_aggregated=True,
        connections_health=True,
        connections_realtime=True,
        heart_metrics=True,
        traces=True,
        cost_tracking=True,
        budget_alerts=True,
        agent_requests=False,  # Editor+ only
        ai_suggestions=True,
        orchestrator_status=True,
        llm_streaming=True,
        session_metrics=True,
    )


def create_fail_closed_permissions() -> WebSocketPermissions:
    """Create fail-closed permissions when OpenFGA is unavailable (0/17)."""
    return WebSocketPermissions(
        alerts=False,
        notifications=False,
        devtools=False,
        audit=False,
        mcp_tasks=False,
        mcp_aggregated=False,
        connections_health=False,
        connections_realtime=False,
        heart_metrics=False,
        traces=False,
        cost_tracking=False,
        budget_alerts=False,
        agent_requests=False,
        ai_suggestions=False,
        orchestrator_status=False,
        llm_streaming=False,
        session_metrics=False,
    )


# ==============================================================================
# Tests for GET /api/v1/me WebSocket Permissions
# ==============================================================================


@pytest.mark.unit
class TestWebSocketPermissionsInMeEndpoint:
    """Tests for websocket_permissions field in GET /api/v1/me response."""

    def test_me_endpoint_returns_websocket_permissions_field(self, mock_alice_user: dict[str, Any]) -> None:
        """Verify /api/v1/me response includes websocket_permissions field."""
        app = create_app_with_user(mock_alice_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_developer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        data = response.json()
        assert "websocket_permissions" in data
        assert isinstance(data["websocket_permissions"], dict)

    def test_me_endpoint_returns_all_17_permission_fields(self, mock_alice_user: dict[str, Any]) -> None:
        """Verify all 17 WebSocket permission fields are returned."""
        app = create_app_with_user(mock_alice_user)

        expected_fields = [
            "alerts",
            "notifications",
            "devtools",
            "audit",
            "mcp_tasks",
            "mcp_aggregated",
            "connections_health",
            "connections_realtime",
            "heart_metrics",
            "traces",
            "cost_tracking",
            "budget_alerts",
            "agent_requests",
            "ai_suggestions",
            "orchestrator_status",
            "llm_streaming",
            "session_metrics",
        ]

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_developer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Verify all expected fields are present
        for field in expected_fields:
            assert field in perms, f"Missing permission field: {field}"

        # Verify exactly 17 fields (no extras)
        assert len(perms) == 17

    def test_admin_user_gets_all_permissions_true(self, mock_admin_user: dict[str, Any]) -> None:
        """Admin user should have all WebSocket permissions including alerts."""
        app = create_app_with_user(mock_admin_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_admin_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Admin has ALL permissions including alerts
        assert perms["alerts"] is True
        assert perms["notifications"] is True
        assert perms["devtools"] is True
        assert perms["agent_requests"] is True

        # All should be True
        assert all(perms.values()), "Admin should have all permissions True"

    def test_developer_user_lacks_alert_permission(self, mock_alice_user: dict[str, Any]) -> None:
        """Developer user should NOT have alert WebSocket permission."""
        app = create_app_with_user(mock_alice_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_developer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Developer lacks admin on dashboard:alerts
        assert perms["alerts"] is False

        # But has most other permissions
        assert perms["notifications"] is True
        assert perms["connections_health"] is True
        assert perms["agent_requests"] is True  # Editor on workflow:hitl

    def test_basic_user_has_viewer_permissions(self, mock_bob_user: dict[str, Any]) -> None:
        """Basic user (bob) should have viewer-level WebSocket permissions (15/17)."""
        app = create_app_with_user(mock_bob_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_basic_user_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Bob lacks admin/editor-only permissions
        assert perms["alerts"] is False  # Admin only
        assert perms["agent_requests"] is False  # Editor only (HITL approval)

        # But has viewer-level permissions (most WebSockets)
        assert perms["notifications"] is True
        assert perms["devtools"] is True  # Viewer access
        assert perms["audit"] is True  # Viewer access
        assert perms["mcp_tasks"] is True
        assert perms["connections_health"] is True
        assert perms["ai_suggestions"] is True
        assert perms["llm_streaming"] is True
        assert perms["session_metrics"] is True

    def test_openfga_unavailable_returns_fail_closed_permissions(self, mock_alice_user: dict[str, Any]) -> None:
        """When OpenFGA is unavailable, should return fail-closed (all False)."""
        app = create_app_with_user(mock_alice_user)

        # Simulate OpenFGA failure by returning fail-closed permissions
        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_fail_closed_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # All permissions should be False (fail-closed)
        assert all(v is False for v in perms.values()), "Fail-closed should have all permissions False"

    def test_response_uses_snake_case_keys(self, mock_alice_user: dict[str, Any]) -> None:
        """Response should use snake_case keys for frontend compatibility."""
        app = create_app_with_user(mock_alice_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_developer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Verify snake_case (underscore) not camelCase
        assert "connections_health" in perms  # Not connectionsHealth
        assert "heart_metrics" in perms  # Not heartMetrics
        assert "budget_alerts" in perms  # Not budgetAlerts
        assert "agent_requests" in perms  # Not agentRequests
        assert "ai_suggestions" in perms  # Not aiSuggestions
        assert "orchestrator_status" in perms  # Not orchestratorStatus

    def test_me_endpoint_calls_get_websocket_permissions_with_user_id(self, mock_alice_user: dict[str, Any]) -> None:
        """Verify get_websocket_permissions is called with correct user_id."""
        app = create_app_with_user(mock_alice_user)

        mock_get_perms = AsyncMock(return_value=create_developer_permissions())

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            mock_get_perms,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200

        # Verify get_websocket_permissions was called with alice's user_id
        mock_get_perms.assert_called_once_with("user:alice")

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestWebSocketPermissionsSchema:
    """Tests for WebSocket permissions schema validation."""

    def test_websocket_permissions_model_has_all_fields(self) -> None:
        """WebSocketPermissions model should have all 17 permission fields."""
        expected_fields = {
            "alerts",
            "notifications",
            "devtools",
            "audit",
            "mcp_tasks",
            "mcp_aggregated",
            "connections_health",
            "connections_realtime",
            "heart_metrics",
            "traces",
            "cost_tracking",
            "budget_alerts",
            "agent_requests",
            "ai_suggestions",
            "orchestrator_status",
            "llm_streaming",
            "session_metrics",
        }

        actual_fields = set(WebSocketPermissions.model_fields.keys())

        assert actual_fields == expected_fields

    def test_websocket_permissions_default_to_false(self) -> None:
        """All WebSocket permission fields should default to False."""
        perms = WebSocketPermissions()

        for field_name in WebSocketPermissions.model_fields:
            assert getattr(perms, field_name) is False, f"{field_name} should default to False"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestWebSocketPermissionsMapping:
    """Tests for WEBSOCKET_PERMISSIONS_MAP alignment with OpenFGA model."""

    def test_permissions_map_has_all_17_entries(self) -> None:
        """WEBSOCKET_PERMISSIONS_MAP should have exactly 17 entries."""
        from mcp_server_langgraph.api.v1.user import WEBSOCKET_PERMISSIONS_MAP

        assert len(WEBSOCKET_PERMISSIONS_MAP) == 17

    def test_permissions_map_keys_match_model_fields(self) -> None:
        """WEBSOCKET_PERMISSIONS_MAP keys should match WebSocketPermissions fields."""
        from mcp_server_langgraph.api.v1.user import WEBSOCKET_PERMISSIONS_MAP

        map_keys = set(WEBSOCKET_PERMISSIONS_MAP.keys())
        model_fields = set(WebSocketPermissions.model_fields.keys())

        assert map_keys == model_fields, (
            f"Mismatch between WEBSOCKET_PERMISSIONS_MAP keys and WebSocketPermissions fields. "
            f"In map but not model: {map_keys - model_fields}. "
            f"In model but not map: {model_fields - map_keys}"
        )

    def test_permissions_map_values_are_valid_tuples(self) -> None:
        """WEBSOCKET_PERMISSIONS_MAP values should be (object_type, object_id, relation) tuples."""
        from mcp_server_langgraph.api.v1.user import WEBSOCKET_PERMISSIONS_MAP

        for key, value in WEBSOCKET_PERMISSIONS_MAP.items():
            assert isinstance(value, tuple), f"{key} value should be a tuple"
            assert len(value) == 3, f"{key} tuple should have exactly 3 elements"

            object_type, object_id, relation = value
            assert isinstance(object_type, str), f"{key} object_type should be a string"
            assert isinstance(object_id, str), f"{key} object_id should be a string"
            assert isinstance(relation, str), f"{key} relation should be a string"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestWebSocketPermissionsIntegration:
    """Integration-level tests for the permissions flow."""

    def test_me_response_structure_matches_frontend_expectations(self, mock_alice_user: dict[str, Any]) -> None:
        """
        Response structure should match what frontend initializeAuth expects.

        Frontend transforms snake_case to camelCase in authSlice.ts:
        - websocket_permissions → websocketPermissions
        - connections_health → connectionsHealth
        """
        app = create_app_with_user(mock_alice_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_developer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level fields expected by frontend
        assert "user_id" in data
        assert "username" in data
        assert "websocket_permissions" in data
        assert "persona" in data

        # websocket_permissions is a nested object
        perms = data["websocket_permissions"]
        assert isinstance(perms, dict)
        assert len(perms) == 17

    def test_permissions_can_be_serialized_to_json(self) -> None:
        """WebSocketPermissions should be JSON-serializable for API response."""
        perms = create_developer_permissions()

        # Pydantic model_dump should work
        perms_dict = perms.model_dump()

        assert isinstance(perms_dict, dict)
        assert len(perms_dict) == 17

        # All values should be booleans
        for key, value in perms_dict.items():
            assert isinstance(value, bool), f"{key} should be boolean, got {type(value)}"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


# ==============================================================================
# Sub-Persona Fixtures and Permission Creators
# ==============================================================================


@pytest.fixture
def mock_auditor_user() -> dict[str, Any]:
    """Mock auditor sub-persona user (admin role, restricted to compliance)."""
    return {
        "user_id": "user:auditor-jane",
        "username": "auditor-jane",
        "email": "jane@example.com",
        "roles": ["admin"],
        "persona": "admin",
        "sub_persona": "auditor",
    }


@pytest.fixture
def mock_compliance_officer_user() -> dict[str, Any]:
    """Mock compliance officer sub-persona user (developer role, compliance focus)."""
    return {
        "user_id": "user:compliance-charlie",
        "username": "compliance-charlie",
        "email": "charlie@example.com",
        "roles": ["developer"],
        "persona": "developer",
        "sub_persona": "compliance-officer",
    }


@pytest.fixture
def mock_devops_user() -> dict[str, Any]:
    """Mock devops sub-persona user (developer role + alerts access)."""
    return {
        "user_id": "user:devops-dave",
        "username": "devops-dave",
        "email": "dave@example.com",
        "roles": ["developer"],
        "persona": "developer",
        "sub_persona": "alice-devops",
    }


def create_auditor_permissions() -> WebSocketPermissions:
    """
    Create permissions for auditor sub-persona.

    Auditors have READ-ONLY compliance access (10/17):
    - YES: audit, traces, notifications, devtools, cost_tracking, heart_metrics,
           session_metrics, llm_streaming, orchestrator_status, budget_alerts
    - NO: alerts (ops), agent_requests (HITL), ai_suggestions (dev),
          mcp_tasks (dev), mcp_aggregated (dev), connections_health (ops),
          connections_realtime (ops)
    """
    return WebSocketPermissions(
        # Compliance-focused access (YES)
        audit=True,
        traces=True,
        notifications=True,
        devtools=True,
        cost_tracking=True,
        heart_metrics=True,
        llm_streaming=True,
        session_metrics=True,
        orchestrator_status=True,
        budget_alerts=True,
        # Operational/Developer features (NO)
        alerts=False,  # Infrastructure ops - not audit
        agent_requests=False,  # HITL approval is operational
        ai_suggestions=False,  # Developer feature
        mcp_tasks=False,  # Developer feature
        mcp_aggregated=False,  # Developer feature
        connections_health=False,  # Ops monitoring
        connections_realtime=False,  # Ops monitoring
    )


def create_compliance_officer_permissions() -> WebSocketPermissions:
    """
    Create permissions for compliance officer sub-persona.

    Compliance officers have READ-ONLY compliance access (10/17):
    Same as auditor - compliance focus without developer privileges.
    """
    return WebSocketPermissions(
        # Compliance-focused access (YES)
        audit=True,
        traces=True,
        notifications=True,
        devtools=True,
        cost_tracking=True,
        heart_metrics=True,
        llm_streaming=True,
        session_metrics=True,
        orchestrator_status=True,
        budget_alerts=True,
        # Operational/Developer features (NO)
        alerts=False,  # Infrastructure ops
        agent_requests=False,  # HITL approval is developer work
        ai_suggestions=False,  # Developer feature
        mcp_tasks=False,  # Developer feature
        mcp_aggregated=False,  # Developer feature
        connections_health=False,  # Developer/ops feature
        connections_realtime=False,  # Developer/ops feature
    )


def create_devops_permissions() -> WebSocketPermissions:
    """
    Create permissions for devops sub-persona.

    DevOps has full developer access PLUS alerts (17/17):
    - All developer permissions (16)
    - PLUS: alerts for infrastructure monitoring during deployments
    """
    return WebSocketPermissions(
        # Full access including alerts
        alerts=True,  # Added for production deployments
        notifications=True,
        devtools=True,
        audit=True,
        mcp_tasks=True,
        mcp_aggregated=True,
        connections_health=True,
        connections_realtime=True,
        heart_metrics=True,
        traces=True,
        cost_tracking=True,
        budget_alerts=True,
        agent_requests=True,
        ai_suggestions=True,
        orchestrator_status=True,
        llm_streaming=True,
        session_metrics=True,
    )


# ==============================================================================
# Tests for Sub-Persona WebSocket Permissions
# ==============================================================================


@pytest.mark.unit
class TestSubPersonaWebSocketPermissions:
    """
    Tests for sub-persona-specific WebSocket permissions.

    Sub-personas allow fine-grained access control beyond base roles:
    - Auditor: Admin role but restricted to compliance-focused access
    - Compliance Officer: Developer role but restricted to compliance
    - DevOps: Developer role plus infrastructure alerts
    """

    def test_auditor_lacks_hitl_approval_permission(self, mock_auditor_user: dict[str, Any]) -> None:
        """
        Auditors should NOT have HITL approval (agent_requests) permission.

        Rationale: Auditors observe and report, they don't make operational decisions.
        """
        app = create_app_with_user(mock_auditor_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_auditor_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Auditor should NOT have HITL approval
        assert perms["agent_requests"] is False, "Auditors should not approve HITL requests"

        # But should have audit access
        assert perms["audit"] is True, "Auditors need audit log access"
        assert perms["traces"] is True, "Auditors need traces for investigation"

    def test_auditor_lacks_infrastructure_alerts(self, mock_auditor_user: dict[str, Any]) -> None:
        """
        Auditors should NOT receive infrastructure alerts.

        Rationale: Infrastructure alerts are for ops, not compliance auditing.
        """
        app = create_app_with_user(mock_auditor_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_auditor_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Auditor should NOT have alerts
        assert perms["alerts"] is False, "Auditors don't need infrastructure alerts"

    def test_auditor_lacks_developer_features(self, mock_auditor_user: dict[str, Any]) -> None:
        """
        Auditors should NOT have developer-only features.

        Rationale: Auditors observe; they don't use AI suggestions or manage MCP.
        """
        app = create_app_with_user(mock_auditor_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_auditor_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Developer-only features should be False
        assert perms["ai_suggestions"] is False, "AI suggestions is developer-only"
        assert perms["mcp_tasks"] is False, "MCP tasks is developer-only"
        assert perms["mcp_aggregated"] is False, "MCP aggregated is developer-only"
        assert perms["connections_health"] is False, "Connection health is ops-only"
        assert perms["connections_realtime"] is False, "Connection realtime is ops-only"

    def test_auditor_has_compliance_access(self, mock_auditor_user: dict[str, Any]) -> None:
        """Auditors should have all compliance-relevant WebSocket access."""
        app = create_app_with_user(mock_auditor_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_auditor_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Compliance-relevant access
        assert perms["audit"] is True
        assert perms["traces"] is True
        assert perms["cost_tracking"] is True
        assert perms["budget_alerts"] is True
        assert perms["heart_metrics"] is True
        assert perms["notifications"] is True
        assert perms["devtools"] is True  # Read-only observability
        assert perms["orchestrator_status"] is True
        assert perms["llm_streaming"] is True
        assert perms["session_metrics"] is True

        # Count: should have exactly 10 permissions
        true_count = sum(1 for v in perms.values() if v is True)
        assert true_count == 10, f"Auditor should have 10/17 permissions, got {true_count}"

    def test_compliance_officer_lacks_developer_features(self, mock_compliance_officer_user: dict[str, Any]) -> None:
        """
        Compliance officers should NOT have developer-only features.

        Rationale: Compliance officers focus on compliance reporting, not development.
        """
        app = create_app_with_user(mock_compliance_officer_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_compliance_officer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Should NOT have developer-only features
        assert perms["agent_requests"] is False, "HITL approval is developer work"
        assert perms["ai_suggestions"] is False, "AI suggestions is developer-only"
        assert perms["mcp_tasks"] is False, "MCP tasks is developer-only"
        assert perms["mcp_aggregated"] is False, "MCP aggregated is developer-only"
        assert perms["connections_health"] is False, "Connection health is dev/ops"
        assert perms["connections_realtime"] is False, "Connection realtime is dev/ops"
        assert perms["alerts"] is False, "Alerts is infrastructure ops"

    def test_compliance_officer_has_compliance_access(self, mock_compliance_officer_user: dict[str, Any]) -> None:
        """Compliance officers should have compliance-relevant WebSocket access."""
        app = create_app_with_user(mock_compliance_officer_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_compliance_officer_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # Compliance-relevant access (same as auditor)
        assert perms["audit"] is True
        assert perms["traces"] is True
        assert perms["cost_tracking"] is True
        assert perms["budget_alerts"] is True

        # Count: should have exactly 10 permissions
        true_count = sum(1 for v in perms.values() if v is True)
        assert true_count == 10, f"Compliance officer should have 10/17 permissions, got {true_count}"

    def test_devops_has_full_developer_plus_alerts(self, mock_devops_user: dict[str, Any]) -> None:
        """
        DevOps sub-persona should have developer access PLUS infrastructure alerts.

        Rationale: DevOps needs to monitor infrastructure during deployments.
        """
        app = create_app_with_user(mock_devops_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_devops_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        # DevOps has alerts (unlike regular developer)
        assert perms["alerts"] is True, "DevOps needs alerts for production deployments"

        # DevOps has all developer permissions
        assert perms["agent_requests"] is True, "DevOps can approve HITL during deployments"
        assert perms["ai_suggestions"] is True
        assert perms["mcp_tasks"] is True
        assert perms["connections_health"] is True
        assert perms["connections_realtime"] is True

        # All 17 permissions should be True
        assert all(perms.values()), "DevOps should have all 17 permissions True"

    def test_devops_has_all_17_permissions(self, mock_devops_user: dict[str, Any]) -> None:
        """DevOps should have full access (17/17) like admin."""
        app = create_app_with_user(mock_devops_user)

        with patch(
            "mcp_server_langgraph.api.v1.user.get_websocket_permissions",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: create_devops_permissions(),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/me")

        assert response.status_code == 200
        perms = response.json()["websocket_permissions"]

        true_count = sum(1 for v in perms.values() if v is True)
        assert true_count == 17, f"DevOps should have 17/17 permissions, got {true_count}"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestSubPersonaPermissionCounts:
    """Verify permission counts for each sub-persona role."""

    @pytest.mark.parametrize(
        "persona,expected_count,description",
        [
            ("admin", 17, "Full platform administrator"),
            ("developer", 16, "Developer without alerts"),
            ("user", 15, "Basic user without alerts/agent_requests"),
            ("auditor", 10, "Compliance-focused, read-only"),
            ("compliance-officer", 10, "Compliance-focused, no dev features"),
            ("devops", 17, "Developer + infrastructure alerts"),
        ],
    )
    def test_permission_count_by_persona(self, persona: str, expected_count: int, description: str) -> None:
        """Verify each persona has the expected number of permissions."""
        permission_creators = {
            "admin": create_admin_permissions,
            "developer": create_developer_permissions,
            "user": create_basic_user_permissions,
            "auditor": create_auditor_permissions,
            "compliance-officer": create_compliance_officer_permissions,
            "devops": create_devops_permissions,
        }

        perms = permission_creators[persona]()
        true_count = sum(1 for v in perms.model_dump().values() if v is True)

        assert true_count == expected_count, (
            f"{description} ({persona}) should have {expected_count}/17 permissions, got {true_count}"
        )

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
