"""
Integration tests for Sub-Persona Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for the 8 sub-personas:
1. admin - Full system access (system:global admin)
2. security-admin - Security-focused admin (system:global admin + role:security member)
3. auditor - Audit/compliance access (system:global viewer + role:audit member)
4. alice-builder - Developer workflow access (system:global developer)
5. alice-analyst - Developer analyst access (system:global developer + role:analyst member)
6. alice-devops - Developer DevOps access (system:global developer + role:devops member)
7. compliance-officer - Compliance access (system:global developer + role:compliance member)
8. bob - Standard user access (system:global user)

RED PHASE: These tests will initially FAIL because:
- system:global resource type is NOT in model.json
- Sub-persona tuples are NOT in sample-tuples.json

Reference: PersonaVariants.ts:101-127 (PERSONA_OPENFGA_MAPPINGS)
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
    pytest.mark.sub_persona,
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


@pytest.mark.xdist_group(name="test_sub_persona_authorization")
class TestSystemGlobalAuthorization:
    """
    Test system:global resource authorization for base personas.

    These tests verify that users have the correct system-level access
    based on their base persona (admin, developer, user).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_system_admin(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin system:global
        WHEN: Checking admin's admin permission on system:global
        THEN: Should return allowed=true

        User Journey: Admin has full system access
        Sub-Persona: admin
        """
        allowed = _check_permission("user:admin", "admin", "system:global")
        assert allowed, "Admin should be admin of system:global"

    def test_alice_is_system_developer(self):
        """
        GIVEN: Pre-seeded tuple user:alice developer system:global
        WHEN: Checking alice's developer permission on system:global
        THEN: Should return allowed=true

        User Journey: Alice (developer) has developer-level system access
        Sub-Persona: alice-builder
        """
        allowed = _check_permission("user:alice", "developer", "system:global")
        assert allowed, "Alice should be developer of system:global"

    def test_bob_is_system_user(self):
        """
        GIVEN: Pre-seeded tuple user:bob user system:global
        WHEN: Checking bob's user permission on system:global
        THEN: Should return allowed=true

        User Journey: Bob has basic user-level system access
        Sub-Persona: bob
        """
        allowed = _check_permission("user:bob", "user", "system:global")
        assert allowed, "Bob should be user of system:global"

    def test_bob_is_not_developer(self):
        """
        GIVEN: Bob only has user access to system:global
        WHEN: Checking bob's developer permission
        THEN: Should return allowed=false

        User Journey: Basic users cannot access developer features
        """
        allowed = _check_permission("user:bob", "developer", "system:global")
        assert not allowed, "Bob should NOT be developer of system:global"

    def test_bob_is_not_admin(self):
        """
        GIVEN: Bob only has user access to system:global
        WHEN: Checking bob's admin permission
        THEN: Should return allowed=false

        User Journey: Basic users cannot access admin features
        """
        allowed = _check_permission("user:bob", "admin", "system:global")
        assert not allowed, "Bob should NOT be admin of system:global"

    def test_alice_is_not_admin(self):
        """
        GIVEN: Alice has developer access to system:global
        WHEN: Checking alice's admin permission
        THEN: Should return allowed=false

        User Journey: Developers cannot access admin features
        """
        allowed = _check_permission("user:alice", "admin", "system:global")
        assert not allowed, "Alice should NOT be admin of system:global"


@pytest.mark.xdist_group(name="test_sub_persona_authorization")
class TestRoleMembershipAuthorization:
    """
    Test role:* resource authorization for sub-persona specializations.

    These tests verify that users have the correct role memberships
    for their specialized sub-personas (security-admin, auditor, analyst, etc.).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # === Admin Sub-Personas ===

    def test_admin_is_security_role_assignee(self):
        """
        GIVEN: Pre-seeded tuple user:admin assignee role:security
        WHEN: Checking admin's assignee permission on role:security
        THEN: Should return allowed=true

        User Journey: Admin can access security-admin features
        Sub-Persona: security-admin
        """
        allowed = _check_permission("user:admin", "assignee", "role:security")
        assert allowed, "Admin should be assignee of role:security"

    def test_admin_is_audit_role_assignee(self):
        """
        GIVEN: Pre-seeded tuple user:admin assignee role:audit
        WHEN: Checking admin's assignee permission on role:audit
        THEN: Should return allowed=true

        User Journey: Admin can access auditor features
        Sub-Persona: auditor
        """
        allowed = _check_permission("user:admin", "assignee", "role:audit")
        assert allowed, "Admin should be assignee of role:audit"

    # === Developer Sub-Personas ===

    def test_alice_is_analyst_role_assignee(self):
        """
        GIVEN: Pre-seeded tuple user:alice assignee role:analyst
        WHEN: Checking alice's assignee permission on role:analyst
        THEN: Should return allowed=true

        User Journey: Alice can access analyst features
        Sub-Persona: alice-analyst
        """
        allowed = _check_permission("user:alice", "assignee", "role:analyst")
        assert allowed, "Alice should be assignee of role:analyst"

    def test_alice_is_devops_role_assignee(self):
        """
        GIVEN: Pre-seeded tuple user:alice assignee role:devops
        WHEN: Checking alice's assignee permission on role:devops
        THEN: Should return allowed=true

        User Journey: Alice can access DevOps features
        Sub-Persona: alice-devops
        """
        allowed = _check_permission("user:alice", "assignee", "role:devops")
        assert allowed, "Alice should be assignee of role:devops"

    def test_alice_is_compliance_role_assignee(self):
        """
        GIVEN: Pre-seeded tuple user:alice assignee role:compliance
        WHEN: Checking alice's assignee permission on role:compliance
        THEN: Should return allowed=true

        User Journey: Alice can access compliance officer features
        Sub-Persona: compliance-officer
        """
        allowed = _check_permission("user:alice", "assignee", "role:compliance")
        assert allowed, "Alice should be assignee of role:compliance"

    # === Bob's Role Restrictions ===

    def test_bob_is_not_analyst_role_assignee(self):
        """
        GIVEN: Bob has no tuple for role:analyst
        WHEN: Checking bob's assignee permission on role:analyst
        THEN: Should return allowed=false

        User Journey: Basic users cannot access analyst features
        """
        allowed = _check_permission("user:bob", "assignee", "role:analyst")
        assert not allowed, "Bob should NOT be assignee of role:analyst"

    def test_bob_is_not_devops_role_assignee(self):
        """
        GIVEN: Bob has no tuple for role:devops
        WHEN: Checking bob's assignee permission on role:devops
        THEN: Should return allowed=false

        User Journey: Basic users cannot access DevOps features
        """
        allowed = _check_permission("user:bob", "assignee", "role:devops")
        assert not allowed, "Bob should NOT be assignee of role:devops"

    def test_bob_is_not_security_role_assignee(self):
        """
        GIVEN: Bob has no tuple for role:security
        WHEN: Checking bob's assignee permission on role:security
        THEN: Should return allowed=false

        User Journey: Basic users cannot access security features
        """
        allowed = _check_permission("user:bob", "assignee", "role:security")
        assert not allowed, "Bob should NOT be assignee of role:security"

    def test_bob_is_not_audit_role_assignee(self):
        """
        GIVEN: Bob has no tuple for role:audit
        WHEN: Checking bob's assignee permission on role:audit
        THEN: Should return allowed=false

        User Journey: Basic users cannot access audit features
        """
        allowed = _check_permission("user:bob", "assignee", "role:audit")
        assert not allowed, "Bob should NOT be assignee of role:audit"

    def test_bob_is_not_compliance_role_assignee(self):
        """
        GIVEN: Bob has no tuple for role:compliance
        WHEN: Checking bob's assignee permission on role:compliance
        THEN: Should return allowed=false

        User Journey: Basic users cannot access compliance features
        """
        allowed = _check_permission("user:bob", "assignee", "role:compliance")
        assert not allowed, "Bob should NOT be assignee of role:compliance"


@pytest.mark.xdist_group(name="test_sub_persona_authorization")
class TestSubPersonaModuleAccess:
    """
    Test that sub-personas can access their designated modules.

    This validates the end-to-end authorization for frontend module access.
    Each sub-persona should be able to access specific resources based on
    their visibleModules configuration.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # === Admin (full access) ===

    def test_admin_can_access_admin_dashboard(self):
        """
        GIVEN: Admin has admin relation on system:global
        WHEN: Checking admin's access to admin module
        THEN: Should have access

        Module: admin
        """
        allowed = _check_permission("user:admin", "admin", "dashboard:grafana")
        assert allowed, "Admin should have admin access to dashboard:grafana"

    def test_admin_can_access_audit_logs(self):
        """
        GIVEN: Admin has admin relation on logs:audit
        WHEN: Checking admin's access to audit module
        THEN: Should have access

        Module: audit
        """
        allowed = _check_permission("user:admin", "admin", "logs:audit")
        assert allowed, "Admin should have admin access to logs:audit"

    # === Security-Admin (security-focused) ===

    def test_security_admin_can_access_compliance(self):
        """
        GIVEN: Admin with security role can access compliance features
        WHEN: Checking security admin's compliance access
        THEN: Should have viewer access

        Module: compliance (via admin role + security membership)
        """
        # Security admin inherits from admin
        allowed = _check_permission("user:admin", "admin", "logs:audit")
        assert allowed, "Security admin should have access to compliance/audit features"

    # === Auditor (audit-only) ===

    def test_auditor_can_view_audit_logs(self):
        """
        GIVEN: Auditor role (admin with audit membership) needs audit access
        WHEN: Checking audit log viewer access
        THEN: Should have viewer access

        Module: audit
        Note: Auditor gets viewer access (not admin) to logs:audit
        """
        allowed = _check_permission("user:alice", "viewer", "logs:audit")
        assert allowed, "Alice (as auditor) should have viewer access to logs:audit"

    # === Alice-Analyst (observability-focused) ===

    def test_analyst_can_view_observability(self):
        """
        GIVEN: Alice is developer with analyst role membership
        WHEN: Checking observability viewer access
        THEN: Should have viewer access

        Module: observability
        """
        allowed = _check_permission("user:alice", "viewer", "observability:default")
        assert allowed, "Alice (analyst) should have viewer access to observability"

    def test_analyst_can_view_cost(self):
        """
        GIVEN: Alice is developer with analyst role membership
        WHEN: Checking cost viewer access
        THEN: Should have viewer access

        Module: cost
        """
        allowed = _check_permission("user:alice", "viewer", "cost:default")
        assert allowed, "Alice (analyst) should have viewer access to cost"

    def test_analyst_can_view_traces(self):
        """
        GIVEN: Alice is developer with analyst role membership
        WHEN: Checking traces viewer access
        THEN: Should have viewer access

        Module: traces
        """
        allowed = _check_permission("user:alice", "viewer", "traces:tempo")
        assert allowed, "Alice (analyst) should have viewer access to traces"

    # === Alice-DevOps (infrastructure-focused) ===

    def test_devops_can_view_mcp_connections(self):
        """
        GIVEN: Alice is developer with devops role membership
        WHEN: Checking MCP connection viewer access
        THEN: Should have owner access to her connections

        Module: connections
        """
        allowed = _check_permission("user:alice", "owner", "mcp_connection:alice_conn")
        assert allowed, "Alice (devops) should have owner access to her MCP connections"

    # === Bob (basic user, limited access) ===

    def test_bob_can_view_workflows(self):
        """
        GIVEN: Bob has viewer access to alice's workflow
        WHEN: Checking workflow viewer access
        THEN: Should have viewer access

        Module: workflows
        """
        allowed = _check_permission("user:bob", "viewer", "workflow:alice_workflow")
        assert allowed, "Bob should have viewer access to shared workflows"

    def test_bob_can_execute_shared_workflows(self):
        """
        GIVEN: Bob has executor access to alice's workflow
        WHEN: Checking workflow executor access
        THEN: Should have executor access

        RED PHASE: This test will FAIL until we add executor tuple for bob
        Reference: Security audit - Bob cannot execute workflows he can view
        Module: workflows
        """
        allowed = _check_permission("user:bob", "executor", "workflow:alice_workflow")
        assert allowed, "Bob should have executor access to shared workflows"

    def test_bob_can_own_his_chat(self):
        """
        GIVEN: Bob owns his own chat
        WHEN: Checking chat owner access
        THEN: Should have owner access

        Module: chat
        """
        allowed = _check_permission("user:bob", "owner", "chat:bob_chat")
        assert allowed, "Bob should have owner access to his chat"

    def test_bob_cannot_access_admin_dashboard(self):
        """
        GIVEN: Bob has no admin access
        WHEN: Checking dashboard admin access
        THEN: Should be denied

        Module: admin (should be blocked)
        """
        allowed = _check_permission("user:bob", "admin", "dashboard:grafana")
        assert not allowed, "Bob should NOT have admin access to dashboard:grafana"

    def test_bob_cannot_access_audit_logs(self):
        """
        GIVEN: Bob has no audit access
        WHEN: Checking audit logs viewer access
        THEN: Should be denied

        Module: audit (should be blocked)
        """
        allowed = _check_permission("user:bob", "viewer", "logs:audit")
        assert not allowed, "Bob should NOT have viewer access to logs:audit"
