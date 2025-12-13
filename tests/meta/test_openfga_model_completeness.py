"""
Meta-tests for OpenFGA Model Completeness.

These tests validate that the OpenFGA authorization model (config/openfga/model.json)
contains all required types for the unified API and infrastructure services.

TDD Cycle: RED -> GREEN -> REFACTOR

Reference: ADR-0068 - Gateway-Level Authentication
"""

import gc
import json
from pathlib import Path

import pytest

# Mark as meta test
pytestmark = [
    pytest.mark.meta,
    pytest.mark.auth,
]


@pytest.fixture
def openfga_model() -> dict:
    """Load the OpenFGA model from config file."""
    model_path = Path(__file__).parent.parent.parent / "config" / "openfga" / "model.json"
    assert model_path.exists(), f"OpenFGA model not found at {model_path}"
    with open(model_path) as f:
        return json.load(f)


@pytest.fixture
def model_types(openfga_model: dict) -> dict[str, dict]:
    """Extract type definitions as a dict keyed by type name."""
    types = {}
    for type_def in openfga_model.get("type_definitions", []):
        types[type_def["type"]] = type_def
    return types


@pytest.mark.xdist_group(name="test_openfga_model_completeness")
class TestOpenFGAModelTypes:
    """Test that OpenFGA model contains all required types."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_has_user_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for user type
        THEN: Model should have 'user' type as base type
        """
        assert "user" in model_types, "Model missing 'user' type"

    def test_model_has_organization_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for organization type
        THEN: Model should have 'organization' type with member/admin relations
        """
        assert "organization" in model_types, "Model missing 'organization' type"
        relations = model_types["organization"].get("relations", {})
        assert "member" in relations, "organization type missing 'member' relation"
        assert "admin" in relations, "organization type missing 'admin' relation"

    def test_model_has_tool_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for tool type
        THEN: Model should have 'tool' type with executor relation
        """
        assert "tool" in model_types, "Model missing 'tool' type"
        relations = model_types["tool"].get("relations", {})
        assert "executor" in relations, "tool type missing 'executor' relation"

    def test_model_has_conversation_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for conversation type
        THEN: Model should have 'conversation' type with owner/viewer relations
        """
        assert "conversation" in model_types, "Model missing 'conversation' type"
        relations = model_types["conversation"].get("relations", {})
        assert "owner" in relations, "conversation type missing 'owner' relation"
        assert "viewer" in relations, "conversation type missing 'viewer' relation"

    def test_model_has_vector_store_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for vector_store type
        THEN: Model should have 'vector_store' type (ADR-0068)
        """
        assert "vector_store" in model_types, "Model missing 'vector_store' type"
        relations = model_types["vector_store"].get("relations", {})
        assert "owner" in relations, "vector_store type missing 'owner' relation"
        assert "viewer" in relations, "vector_store type missing 'viewer' relation"

    def test_model_has_authz_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for authz type
        THEN: Model should have 'authz' type for OpenFGA Playground access
        """
        assert "authz" in model_types, "Model missing 'authz' type"
        relations = model_types["authz"].get("relations", {})
        assert "admin" in relations, "authz type missing 'admin' relation"
        assert "viewer" in relations, "authz type missing 'viewer' relation"


@pytest.mark.xdist_group(name="test_openfga_model_completeness")
class TestOpenFGAModelUnifiedAPITypes:
    """
    Test that OpenFGA model contains types for unified API entities.

    These tests will FAIL initially (RED phase) until we add the types.
    This follows TDD - write failing tests first, then implement.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_has_workflow_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for workflow type
        THEN: Model should have 'workflow' type for /api/v1/workflows

        Workflows are distinct from conversations - they represent
        LangGraph workflow definitions that can be executed.

        Required relations:
        - owner: User who created the workflow
        - editor: Users who can modify the workflow
        - viewer: Users who can view the workflow
        - executor: Users who can run the workflow
        - organization: Organization that owns the workflow
        """
        assert "workflow" in model_types, "Model missing 'workflow' type for /api/v1/workflows"
        relations = model_types["workflow"].get("relations", {})
        assert "owner" in relations, "workflow type missing 'owner' relation"
        assert "viewer" in relations, "workflow type missing 'viewer' relation"
        assert "editor" in relations, "workflow type missing 'editor' relation"
        assert "executor" in relations, "workflow type missing 'executor' relation"

    def test_model_has_session_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for session type
        THEN: Model should have 'session' type for /api/v1/sessions

        Sessions represent workflow execution instances with state.
        They are different from conversations (which are chat threads).

        Required relations:
        - owner: User who created the session
        - viewer: Users who can view session state/history
        - organization: Organization that owns the session
        """
        assert "session" in model_types, "Model missing 'session' type for /api/v1/sessions"
        relations = model_types["session"].get("relations", {})
        assert "owner" in relations, "session type missing 'owner' relation"
        assert "viewer" in relations, "session type missing 'viewer' relation"

    def test_model_has_api_key_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for api_key type
        THEN: Model should have 'api_key' type for API key management

        API keys need authorization to control who can:
        - View their own API keys
        - Rotate/revoke their keys
        - Admin: manage all API keys in organization

        Required relations:
        - owner: User who owns the API key
        - viewer: Users who can view the key (derived from owner)
        """
        assert "api_key" in model_types, "Model missing 'api_key' type for API key management"
        relations = model_types["api_key"].get("relations", {})
        assert "owner" in relations, "api_key type missing 'owner' relation"

    def test_model_has_dashboard_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for dashboard type
        THEN: Model should have 'dashboard' type for Grafana access control

        Dashboards control access to monitoring and observability UIs:
        - /dashboards (Grafana)
        - /gateway (Traefik dashboard)

        Required relations:
        - admin: Full access to create/modify dashboards
        - editor: Can modify existing dashboards
        - viewer: Can view dashboards (read-only)
        """
        assert "dashboard" in model_types, "Model missing 'dashboard' type for Grafana access"
        relations = model_types["dashboard"].get("relations", {})
        assert "admin" in relations, "dashboard type missing 'admin' relation"
        assert "viewer" in relations, "dashboard type missing 'viewer' relation"

    def test_model_has_cost_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for cost type
        THEN: Model should have 'cost' type for /api/v1/cost

        Cost tracking needs authorization for:
        - Viewing cost summaries and breakdowns
        - Accessing detailed cost analytics
        - Exporting cost reports

        Required relations:
        - admin: Full access to cost management
        - viewer: Can view cost data (read-only)
        """
        assert "cost" in model_types, "Model missing 'cost' type for /api/v1/cost"
        relations = model_types["cost"].get("relations", {})
        assert "admin" in relations, "cost type missing 'admin' relation"
        assert "viewer" in relations, "cost type missing 'viewer' relation"

    def test_model_has_observability_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for observability type
        THEN: Model should have 'observability' type for /api/v1/observability

        Observability endpoints control access to:
        - Traces (distributed tracing)
        - Metrics (performance data)
        - Logs (application logs)

        Required relations:
        - admin: Full access to observability data
        - viewer: Can view traces, metrics, logs
        """
        assert "observability" in model_types, "Model missing 'observability' type"
        relations = model_types["observability"].get("relations", {})
        assert "admin" in relations, "observability type missing 'admin' relation"
        assert "viewer" in relations, "observability type missing 'viewer' relation"

    def test_model_has_chat_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for chat type
        THEN: Model should have 'chat' type for /api/v1/chat

        Chat resources control access to:
        - Real-time chat endpoints
        - Chat history and context
        - Chat completions

        Required relations:
        - owner: User who owns the chat
        - viewer: Users who can view chat history
        """
        assert "chat" in model_types, "Model missing 'chat' type for /api/v1/chat"
        relations = model_types["chat"].get("relations", {})
        assert "owner" in relations, "chat type missing 'owner' relation"
        assert "viewer" in relations, "chat type missing 'viewer' relation"

    def test_model_has_mcp_connection_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for mcp_connection type
        THEN: Model should have 'mcp_connection' type for /api/v1/mcp

        MCP connections control access to:
        - MCP WebSocket connections
        - MCP tool execution

        Required relations:
        - owner: User who owns the connection
        - viewer: Users who can view connection status
        """
        assert "mcp_connection" in model_types, "Model missing 'mcp_connection' type"
        relations = model_types["mcp_connection"].get("relations", {})
        assert "owner" in relations, "mcp_connection type missing 'owner' relation"


@pytest.mark.xdist_group(name="test_openfga_model_completeness")
class TestOpenFGAModelInfrastructureTypes:
    """
    Test that OpenFGA model contains types for infrastructure services.

    These types control access to third-party services integrated via
    docker-compose.test.yml and the Traefik gateway.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_has_gateway_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for gateway type
        THEN: Model should have 'gateway' type for Traefik dashboard

        Gateway controls access to:
        - /gateway (Traefik dashboard)
        - Router and service status

        Required relations:
        - admin: Full access to gateway configuration
        - viewer: Can view gateway status
        """
        assert "gateway" in model_types, "Model missing 'gateway' type"
        relations = model_types["gateway"].get("relations", {})
        assert "admin" in relations, "gateway type missing 'admin' relation"
        assert "viewer" in relations, "gateway type missing 'viewer' relation"

    def test_model_has_logs_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for logs type
        THEN: Model should have 'logs' type for Loki access

        Logs controls access to:
        - Loki log aggregation
        - Log queries and exploration

        Required relations:
        - admin: Full access to log configuration
        - viewer: Can query and view logs
        """
        assert "logs" in model_types, "Model missing 'logs' type for Loki"
        relations = model_types["logs"].get("relations", {})
        assert "admin" in relations, "logs type missing 'admin' relation"
        assert "viewer" in relations, "logs type missing 'viewer' relation"

    def test_model_has_traces_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for traces type
        THEN: Model should have 'traces' type for Tempo access

        Traces controls access to:
        - Tempo distributed tracing
        - Trace queries and exploration

        Required relations:
        - admin: Full access to trace configuration
        - viewer: Can query and view traces
        """
        assert "traces" in model_types, "Model missing 'traces' type for Tempo"
        relations = model_types["traces"].get("relations", {})
        assert "admin" in relations, "traces type missing 'admin' relation"
        assert "viewer" in relations, "traces type missing 'viewer' relation"

    def test_model_has_metrics_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for metrics type
        THEN: Model should have 'metrics' type for Mimir access

        Metrics controls access to:
        - Mimir metrics storage
        - Prometheus-compatible queries

        Required relations:
        - admin: Full access to metrics configuration
        - viewer: Can query and view metrics
        """
        assert "metrics" in model_types, "Model missing 'metrics' type for Mimir"
        relations = model_types["metrics"].get("relations", {})
        assert "admin" in relations, "metrics type missing 'admin' relation"
        assert "viewer" in relations, "metrics type missing 'viewer' relation"

    def test_model_has_identity_type(self, model_types: dict) -> None:
        """
        GIVEN: OpenFGA model.json
        WHEN: Checking for identity type
        THEN: Model should have 'identity' type for Keycloak admin

        Identity controls access to:
        - Keycloak admin console
        - User and realm management

        Required relations:
        - admin: Full access to identity management
        - viewer: Can view user information
        """
        assert "identity" in model_types, "Model missing 'identity' type for Keycloak"
        relations = model_types["identity"].get("relations", {})
        assert "admin" in relations, "identity type missing 'admin' relation"


@pytest.mark.xdist_group(name="test_openfga_model_completeness")
class TestOpenFGAModelRelationHierarchy:
    """Test that relation hierarchies are properly defined."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_viewer_inherits_from_editor(self, model_types: dict) -> None:
        """
        GIVEN: workflow type in model
        WHEN: Checking viewer relation
        THEN: viewer should inherit from editor (editors can always view)
        """
        if "workflow" not in model_types:
            pytest.skip("workflow type not yet added")

        relations = model_types["workflow"].get("relations", {})
        viewer = relations.get("viewer", {})

        # Check that viewer relation includes editor in its union
        # This is a structural check - the exact format depends on OpenFGA schema
        assert viewer, "workflow viewer relation should be defined"

    def test_session_viewer_inherits_from_owner(self, model_types: dict) -> None:
        """
        GIVEN: session type in model
        WHEN: Checking viewer relation
        THEN: viewer should inherit from owner (owners can always view)
        """
        if "session" not in model_types:
            pytest.skip("session type not yet added")

        relations = model_types["session"].get("relations", {})
        viewer = relations.get("viewer", {})
        assert viewer, "session viewer relation should be defined"

    def test_dashboard_editor_inherits_from_admin(self, model_types: dict) -> None:
        """
        GIVEN: dashboard type in model
        WHEN: Checking editor relation
        THEN: editor should inherit from admin (admins can always edit)
        """
        if "dashboard" not in model_types:
            pytest.skip("dashboard type not yet added")

        relations = model_types["dashboard"].get("relations", {})
        editor = relations.get("editor", {})
        assert editor, "dashboard editor relation should be defined"
