"""
Integration tests for Observability API Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Observability resources (/api/v1/observability)
2. Cost tracking resources (/api/v1/cost)
3. Traces, metrics, and logs access

RED PHASE: These tests use EXISTING tuples but verify API endpoints
will enforce authorization (currently missing from API layer).

User Journeys:
- Admin: admin of observability:default (full access)
- Alice: viewer of observability:default (read-only)
- Bob: viewer of observability:default (read-only)

Reference: Plan - Phase 5.4: Observability API
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
    pytest.mark.observability,
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


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestObservabilityAdminAccess:
    """
    Test observability admin authorization from sample-tuples.json.

    Admins have full configuration access to observability systems.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_observability_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin observability:default
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure observability settings
        API Endpoint: PUT /api/v1/observability/config
        """
        allowed = _check_permission("user:admin", "admin", "observability:default")
        assert allowed, "Admin should be admin of observability:default"

    def test_admin_can_view_observability(self):
        """
        GIVEN: Admin is admin of observability:default
        WHEN: Checking admin's viewer permission (inherited from admin)
        THEN: Should return allowed=true

        User Journey: Admin can always view observability data
        """
        allowed = _check_permission("user:admin", "viewer", "observability:default")
        assert allowed, "Admin should be viewer (via admin inheritance) of observability:default"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestObservabilityViewerAccess:
    """
    Test observability viewer authorization from sample-tuples.json.

    Viewers can read metrics, traces, and logs but not configure.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_is_observability_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer observability:default
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view traces and metrics
        API Endpoint: GET /api/v1/observability/metrics
        """
        allowed = _check_permission("user:alice", "viewer", "observability:default")
        assert allowed, "Alice should be viewer of observability:default"

    def test_bob_is_observability_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer observability:default
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view traces and metrics
        """
        allowed = _check_permission("user:bob", "viewer", "observability:default")
        assert allowed, "Bob should be viewer of observability:default"

    def test_alice_cannot_admin_observability(self):
        """
        GIVEN: Alice only has viewer access
        WHEN: Checking alice's admin permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot configure observability
        API Endpoint: PUT /api/v1/observability/config should fail for alice
        """
        allowed = _check_permission("user:alice", "admin", "observability:default")
        assert not allowed, "Alice should NOT be admin of observability:default"

    def test_bob_cannot_admin_observability(self):
        """
        GIVEN: Bob only has viewer access
        WHEN: Checking bob's admin permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot configure observability
        """
        allowed = _check_permission("user:bob", "admin", "observability:default")
        assert not allowed, "Bob should NOT be admin of observability:default"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestCostTrackingAccess:
    """
    Test cost tracking authorization from sample-tuples.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_cost_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin cost:default
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can manage cost settings and budgets
        API Endpoint: PUT /api/v1/cost/budget
        """
        allowed = _check_permission("user:admin", "admin", "cost:default")
        assert allowed, "Admin should be admin of cost:default"

    def test_alice_is_cost_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer cost:default
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view cost data
        API Endpoint: GET /api/v1/cost/usage
        """
        allowed = _check_permission("user:alice", "viewer", "cost:default")
        assert allowed, "Alice should be viewer of cost:default"

    def test_bob_is_cost_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer cost:default
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view cost data
        """
        allowed = _check_permission("user:bob", "viewer", "cost:default")
        assert allowed, "Bob should be viewer of cost:default"

    def test_alice_cannot_admin_cost(self):
        """
        GIVEN: Alice only has viewer access
        WHEN: Checking alice's admin permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot set budgets
        """
        allowed = _check_permission("user:alice", "admin", "cost:default")
        assert not allowed, "Alice should NOT be admin of cost:default"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestHEARTMetricsAccess:
    """
    Test HEART metrics WebSocket authorization.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_view_heart_metrics(self):
        """
        GIVEN: Pre-seeded tuple user:admin viewer observability:heart
        WHEN: Checking admin's viewer permission
        THEN: Should return allowed=true

        User Journey: Admin can view HEART metrics
        WebSocket: /api/v1/ws/metrics/heart
        """
        allowed = _check_permission("user:admin", "viewer", "observability:heart")
        assert allowed, "Admin should have viewer access to observability:heart"

    def test_alice_can_view_heart_metrics(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer observability:heart
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view HEART metrics
        """
        allowed = _check_permission("user:alice", "viewer", "observability:heart")
        assert allowed, "Alice should have viewer access to observability:heart"

    def test_bob_can_view_heart_metrics(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer observability:heart
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view HEART metrics
        """
        allowed = _check_permission("user:bob", "viewer", "observability:heart")
        assert allowed, "Bob should have viewer access to observability:heart"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestCostUsageWebSocketAccess:
    """
    Test cost usage WebSocket authorization.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_can_view_cost_usage(self):
        """
        GIVEN: Pre-seeded tuple user:admin viewer cost:usage
        WHEN: Checking admin's viewer permission
        THEN: Should return allowed=true

        User Journey: Admin can view real-time cost usage
        WebSocket: /api/v1/ws/usage/cost
        """
        allowed = _check_permission("user:admin", "viewer", "cost:usage")
        assert allowed, "Admin should have viewer access to cost:usage"

    def test_alice_can_view_cost_usage(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer cost:usage
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can view real-time cost usage
        """
        allowed = _check_permission("user:alice", "viewer", "cost:usage")
        assert allowed, "Alice should have viewer access to cost:usage"

    def test_bob_can_view_cost_usage(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer cost:usage
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can view real-time cost usage
        """
        allowed = _check_permission("user:bob", "viewer", "cost:usage")
        assert allowed, "Bob should have viewer access to cost:usage"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestTracesAccess:
    """
    Test Tempo traces authorization from sample-tuples.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_traces_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin traces:tempo
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Tempo settings
        """
        allowed = _check_permission("user:admin", "admin", "traces:tempo")
        assert allowed, "Admin should be admin of traces:tempo"

    def test_alice_is_traces_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer traces:tempo
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can query traces
        """
        allowed = _check_permission("user:alice", "viewer", "traces:tempo")
        assert allowed, "Alice should be viewer of traces:tempo"

    def test_bob_is_traces_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer traces:tempo
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can query traces
        """
        allowed = _check_permission("user:bob", "viewer", "traces:tempo")
        assert allowed, "Bob should be viewer of traces:tempo"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestLogsAccess:
    """
    Test Loki logs authorization from sample-tuples.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_logs_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin logs:loki
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Loki settings
        """
        allowed = _check_permission("user:admin", "admin", "logs:loki")
        assert allowed, "Admin should be admin of logs:loki"

    def test_alice_is_logs_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer logs:loki
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can query logs
        """
        allowed = _check_permission("user:alice", "viewer", "logs:loki")
        assert allowed, "Alice should be viewer of logs:loki"

    def test_bob_is_logs_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer logs:loki
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can query logs
        """
        allowed = _check_permission("user:bob", "viewer", "logs:loki")
        assert allowed, "Bob should be viewer of logs:loki"


@pytest.mark.xdist_group(name="test_observability_authorization")
class TestMetricsAccess:
    """
    Test Mimir metrics authorization from sample-tuples.json.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_metrics_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin metrics:mimir
        WHEN: Checking admin's admin permission
        THEN: Should return allowed=true

        User Journey: Admin can configure Mimir settings
        """
        allowed = _check_permission("user:admin", "admin", "metrics:mimir")
        assert allowed, "Admin should be admin of metrics:mimir"

    def test_alice_is_metrics_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer metrics:mimir
        WHEN: Checking alice's viewer permission
        THEN: Should return allowed=true

        User Journey: Alice can query metrics
        """
        allowed = _check_permission("user:alice", "viewer", "metrics:mimir")
        assert allowed, "Alice should be viewer of metrics:mimir"

    def test_bob_is_metrics_viewer(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer metrics:mimir
        WHEN: Checking bob's viewer permission
        THEN: Should return allowed=true

        User Journey: Bob can query metrics
        """
        allowed = _check_permission("user:bob", "viewer", "metrics:mimir")
        assert allowed, "Bob should be viewer of metrics:mimir"
