"""
Integration tests for Unified API Authorization Types.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Workflow resources (/api/v1/workflows)
2. Session resources (/api/v1/sessions)
3. Dashboard resources (Grafana)
4. Cost resources (/api/v1/cost)
5. Observability resources (/api/v1/observability)

Tests run against the pre-seeded tuples in config/openfga/sample-tuples.json.

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
    """Check if OpenFGA is available."""
    try:
        response = requests.get(
            "http://localhost:9080/healthz",
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip at module level if OpenFGA not available
if not _openfga_available():
    pytestmark.append(pytest.mark.skip(reason="OpenFGA not available for authorization tests"))

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


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestWorkflowAuthorization:
    """Test workflow authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_owner_of_default_workflow(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner workflow:default
        WHEN: Checking admin's owner permission on workflow:default
        THEN: Should return allowed=true

        User Journey: Admin can manage default workflow
        """
        allowed = _check_permission("user:admin", "owner", "workflow:default")
        assert allowed, "Admin should be owner of workflow:default"

    def test_alice_is_owner_of_her_workflow(self):
        """
        GIVEN: Pre-seeded tuple user:alice owner workflow:alice_workflow
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=true

        User Journey: Alice can manage her own workflow
        """
        allowed = _check_permission("user:alice", "owner", "workflow:alice_workflow")
        assert allowed, "Alice should be owner of workflow:alice_workflow"

    def test_bob_is_viewer_of_alice_workflow(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer workflow:alice_workflow
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view alice's shared workflow
        """
        allowed = _check_permission("user:bob", "viewer", "workflow:alice_workflow")
        assert allowed, "Bob should be viewer of workflow:alice_workflow"

    def test_bob_cannot_own_alice_workflow(self):
        """
        GIVEN: Bob only has viewer access to alice's workflow
        WHEN: Checking bob's owner permission
        THEN: Should return allowed=false

        User Journey: Bob cannot modify alice's workflow
        """
        allowed = _check_permission("user:bob", "owner", "workflow:alice_workflow")
        assert not allowed, "Bob should NOT be owner of workflow:alice_workflow"

    def test_alice_can_view_her_workflow_via_inheritance(self):
        """
        GIVEN: Alice is owner of workflow:alice_workflow
        WHEN: Checking alice's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Owner can always view their workflow
        """
        allowed = _check_permission("user:alice", "viewer", "workflow:alice_workflow")
        assert allowed, "Alice should be viewer (via owner inheritance) of workflow:alice_workflow"


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestSessionAuthorization:
    """Test session authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_owner_of_admin_session(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner session:admin_session
        WHEN: Checking admin's owner permission
        THEN: Should return allowed=true

        User Journey: Admin can manage their session
        """
        allowed = _check_permission("user:admin", "owner", "session:admin_session")
        assert allowed, "Admin should be owner of session:admin_session"

    def test_alice_is_owner_of_alice_session(self):
        """
        GIVEN: Pre-seeded tuple user:alice owner session:alice_session
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=true

        User Journey: Alice can manage her session
        """
        allowed = _check_permission("user:alice", "owner", "session:alice_session")
        assert allowed, "Alice should be owner of session:alice_session"

    def test_bob_is_owner_of_bob_session(self):
        """
        GIVEN: Pre-seeded tuple user:bob owner session:bob_session
        WHEN: Checking bob's owner permission
        THEN: Should return allowed=true

        User Journey: Bob can manage his session
        """
        allowed = _check_permission("user:bob", "owner", "session:bob_session")
        assert allowed, "Bob should be owner of session:bob_session"

    def test_alice_cannot_access_bob_session(self):
        """
        GIVEN: Alice has no tuple for bob's session
        WHEN: Checking alice's owner permission on bob's session
        THEN: Should return allowed=false

        User Journey: Users cannot access other users' sessions
        """
        allowed = _check_permission("user:alice", "owner", "session:bob_session")
        assert not allowed, "Alice should NOT be able to access bob's session"


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestDashboardAuthorization:
    """Test dashboard (Grafana) authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_dashboard_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin dashboard:grafana
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Grafana dashboards
        """
        allowed = _check_permission("user:admin", "admin", "dashboard:grafana")
        assert allowed, "Admin should have admin access to dashboard:grafana"

    def test_alice_is_dashboard_editor(self):
        """
        GIVEN: Pre-seeded tuple user:alice editor dashboard:grafana
        WHEN: Checking alice's editor permission
        THEN: Should return allowed=true

        User Journey: Alice can edit Grafana dashboards
        """
        allowed = _check_permission("user:alice", "editor", "dashboard:grafana")
        assert allowed, "Alice should have editor access to dashboard:grafana"

    def test_bob_is_dashboard_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer dashboard:grafana
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view Grafana dashboards
        """
        allowed = _check_permission("user:bob", "viewer", "dashboard:grafana")
        assert allowed, "Bob should have viewer access to dashboard:grafana"

    def test_bob_cannot_edit_dashboard(self):
        """
        GIVEN: Bob only has viewer access
        WHEN: Checking bob's editor permission
        THEN: Should return allowed=false

        User Journey: Viewer cannot edit dashboards
        """
        allowed = _check_permission("user:bob", "editor", "dashboard:grafana")
        assert not allowed, "Bob should NOT have editor access to dashboard:grafana"

    def test_alice_can_view_via_editor_inheritance(self):
        """
        GIVEN: Alice is editor of dashboard:grafana
        WHEN: Checking alice's viewer permission (inherited from editor)
        THEN: Should return allowed=true

        User Journey: Editor can always view dashboards
        """
        allowed = _check_permission("user:alice", "viewer", "dashboard:grafana")
        assert allowed, "Alice should be viewer (via editor inheritance) of dashboard:grafana"


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestCostAuthorization:
    """Test cost tracking authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_cost_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin cost:default
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can manage cost tracking
        """
        allowed = _check_permission("user:admin", "admin", "cost:default")
        assert allowed, "Admin should have admin access to cost:default"

    def test_alice_is_cost_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer cost:default
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view cost data
        """
        allowed = _check_permission("user:alice", "viewer", "cost:default")
        assert allowed, "Alice should have viewer access to cost:default"

    def test_bob_is_cost_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer cost:default
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view cost data
        """
        allowed = _check_permission("user:bob", "viewer", "cost:default")
        assert allowed, "Bob should have viewer access to cost:default"


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestObservabilityAuthorization:
    """Test observability authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_observability_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin observability:default
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure observability
        """
        allowed = _check_permission("user:admin", "admin", "observability:default")
        assert allowed, "Admin should have admin access to observability:default"

    def test_alice_is_observability_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer observability:default
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view traces and metrics
        """
        allowed = _check_permission("user:alice", "viewer", "observability:default")
        assert allowed, "Alice should have viewer access to observability:default"

    def test_bob_is_observability_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer observability:default
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view traces and metrics
        """
        allowed = _check_permission("user:bob", "viewer", "observability:default")
        assert allowed, "Bob should have viewer access to observability:default"


@pytest.mark.xdist_group(name="test_unified_api_authorization")
class TestInfrastructureAuthorization:
    """Test infrastructure service authorization from sample-tuples.json."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_gateway_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin gateway:traefik
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Traefik gateway
        """
        allowed = _check_permission("user:admin", "admin", "gateway:traefik")
        assert allowed, "Admin should have admin access to gateway:traefik"

    def test_alice_is_gateway_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer gateway:traefik
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view gateway status
        """
        allowed = _check_permission("user:alice", "viewer", "gateway:traefik")
        assert allowed, "Alice should have viewer access to gateway:traefik"

    def test_admin_is_identity_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin identity:keycloak
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can manage Keycloak
        """
        allowed = _check_permission("user:admin", "admin", "identity:keycloak")
        assert allowed, "Admin should have admin access to identity:keycloak"

    def test_alice_cannot_admin_identity(self):
        """
        GIVEN: Alice has no tuple for identity:keycloak
        WHEN: Checking alice's admin permission
        THEN: Should return allowed=false

        User Journey: Non-admins cannot manage identity
        """
        allowed = _check_permission("user:alice", "admin", "identity:keycloak")
        assert not allowed, "Alice should NOT have admin access to identity:keycloak"

    def test_admin_is_logs_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin logs:loki
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Loki
        """
        allowed = _check_permission("user:admin", "admin", "logs:loki")
        assert allowed, "Admin should have admin access to logs:loki"

    def test_alice_is_logs_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer logs:loki
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can query logs
        """
        allowed = _check_permission("user:alice", "viewer", "logs:loki")
        assert allowed, "Alice should have viewer access to logs:loki"

    def test_admin_is_traces_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin traces:tempo
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Tempo
        """
        allowed = _check_permission("user:admin", "admin", "traces:tempo")
        assert allowed, "Admin should have admin access to traces:tempo"

    def test_admin_is_metrics_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin metrics:mimir
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Mimir
        """
        allowed = _check_permission("user:admin", "admin", "metrics:mimir")
        assert allowed, "Admin should have admin access to metrics:mimir"
