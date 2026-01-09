"""
Integration tests for Service Principal Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Service principal permission tuples (direct SP grants)
2. SP metadata parity with user type
3. acts_as relationship tracking

Service Principal Use Cases:
- batch-etl-job: Batch processing SP that executes tools and owns executions

Reference: sample-tuples.json Service Principal section (lines 944-965)
Reference: OpenFGA Audit Resolution Plan Phase 5 (Service Principal Parity)
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
    pytest.mark.service_principal,
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
    """Check if user/service_principal has permission via OpenFGA."""
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


# =============================================================================
# Service Principal Direct Permission Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_service_principal_authorization")
class TestServicePrincipalDirectPermissions:
    """
    Test service principal direct permission tuples from sample-tuples.json.

    Service principals can be granted permissions directly, just like users,
    thanks to Phase 5.1 metadata parity updates.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sp_can_execute_tool(self):
        """
        GIVEN: Pre-seeded tuple service_principal:batch-etl-job executor tool:chat
        WHEN: Checking SP's executor permission on tool:chat
        THEN: Should return allowed=true

        User Journey: Batch ETL job can call MCP tools for data processing
        API Endpoint: POST /api/v1/chat/invoke-tool
        """
        allowed = _check_permission(
            "service_principal:batch-etl-job", "executor", "tool:chat"
        )
        assert allowed, "Service principal should have executor access to tool:chat"

    def test_sp_owns_execution(self):
        """
        GIVEN: Pre-seeded tuple service_principal:batch-etl-job owner execution:default
        WHEN: Checking SP's owner permission on execution:default
        THEN: Should return allowed=true

        User Journey: Batch ETL job owns its workflow executions
        API Endpoint: GET /api/v1/workflow_executions/{id}
        """
        allowed = _check_permission(
            "service_principal:batch-etl-job", "owner", "execution:default"
        )
        assert allowed, "Service principal should own execution:default"

    def test_sp_inherits_viewer_from_owner(self):
        """
        GIVEN: SP has owner relation to execution:default
        WHEN: Checking SP's viewer permission (inherited)
        THEN: Should return allowed=true (owner -> viewer via model)

        User Journey: Batch ETL job can view its own executions
        API Endpoint: GET /api/v1/workflow_executions
        """
        allowed = _check_permission(
            "service_principal:batch-etl-job", "viewer", "execution:default"
        )
        assert allowed, "SP should inherit viewer access via owner relation"


@pytest.mark.xdist_group(name="test_service_principal_authorization")
class TestServicePrincipalActsAs:
    """
    Test service principal acts_as relationship.

    The acts_as tuple links a service principal to its controlling user,
    enabling audit trails and permission delegation tracking.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_acts_as_tuple_exists(self):
        """
        GIVEN: Pre-seeded tuple user:admin acts_as service_principal:batch-etl-job
        WHEN: Checking acts_as relationship
        THEN: Should return allowed=true

        User Journey: Verify admin controls the batch-etl-job SP
        Security: Enables audit trail linking SP actions to controlling user
        """
        allowed = _check_permission(
            "user:admin", "acts_as", "service_principal:batch-etl-job"
        )
        assert allowed, "user:admin should have acts_as on service_principal:batch-etl-job"


@pytest.mark.xdist_group(name="test_service_principal_authorization")
class TestServicePrincipalNegativeCases:
    """
    Negative tests to verify SPs don't have unauthorized access.

    Service principals should only have access to resources they're
    explicitly granted permissions for.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sp_cannot_access_ungranted_resource(self):
        """
        GIVEN: No tuple granting batch-etl-job access to skill:default
        WHEN: Checking SP's admin permission on skill:default
        THEN: Should return allowed=false

        User Journey: SP should not have implicit access to all resources
        Security: Verify least-privilege principle for SPs
        """
        allowed = _check_permission(
            "service_principal:batch-etl-job", "admin", "skill:default"
        )
        assert not allowed, "SP should NOT have access to ungratned resources"

    def test_nonexistent_sp_has_no_access(self):
        """
        GIVEN: No tuples for service_principal:fake-sp
        WHEN: Checking fake SP's permission on any resource
        THEN: Should return allowed=false

        Security: Non-existent service principals have no permissions
        """
        allowed = _check_permission(
            "service_principal:fake-sp", "executor", "tool:chat"
        )
        assert not allowed, "Non-existent SP should have no access"
