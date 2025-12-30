"""
Integration tests for Project API Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Project resources (/api/v1/projects)
2. Project member access levels (owner, editor, viewer)
3. Organization-level project access

RED PHASE: These tests will initially FAIL because:
- No project:* tuples exist in sample-tuples.json

User Journeys:
- Admin: owner of project:default (full CRUD)
- Alice: editor of project:default (read + update)
- Bob: viewer of project:default (read-only)

Reference: Plan - Phase 3: Add Project Resource Tuples
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
    pytest.mark.projects,
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


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectOwnership:
    """
    Test project ownership authorization from sample-tuples.json.

    Owners have full CRUD access to projects.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_owner_of_default_project(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner project:default
        WHEN: Checking admin's owner permission on project:default
        THEN: Should return allowed=true

        User Journey: Admin can manage default project (create, read, update, delete)
        API Endpoint: DELETE /api/v1/projects/{id}
        """
        allowed = _check_permission("user:admin", "owner", "project:default")
        assert allowed, "Admin should be owner of project:default"

    def test_admin_is_owner_of_admin_project(self):
        """
        GIVEN: Pre-seeded tuple user:admin owner project:admin_project
        WHEN: Checking admin's owner permission on project:admin_project
        THEN: Should return allowed=true

        User Journey: Admin has their own project
        """
        allowed = _check_permission("user:admin", "owner", "project:admin_project")
        assert allowed, "Admin should be owner of project:admin_project"

    def test_alice_cannot_own_default_project(self):
        """
        GIVEN: Alice only has editor access to project:default
        WHEN: Checking alice's owner permission
        THEN: Should return allowed=false

        User Journey: Editors cannot delete projects
        API Endpoint: DELETE /api/v1/projects/{id} should fail for alice
        """
        allowed = _check_permission("user:alice", "owner", "project:default")
        assert not allowed, "Alice should NOT be owner of project:default"

    def test_bob_cannot_own_default_project(self):
        """
        GIVEN: Bob only has viewer access to project:default
        WHEN: Checking bob's owner permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot delete projects
        """
        allowed = _check_permission("user:bob", "owner", "project:default")
        assert not allowed, "Bob should NOT be owner of project:default"


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectEditorAccess:
    """
    Test project editor authorization from sample-tuples.json.

    Editors can read and update projects but not delete.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_is_editor_of_default_project(self):
        """
        GIVEN: Pre-seeded tuple user:alice editor project:default
        WHEN: Checking alice's editor permission on project:default
        THEN: Should return allowed=true

        User Journey: Alice can edit default project
        API Endpoint: PUT /api/v1/projects/{id}
        """
        allowed = _check_permission("user:alice", "editor", "project:default")
        assert allowed, "Alice should be editor of project:default"

    def test_admin_can_edit_via_owner_inheritance(self):
        """
        GIVEN: Admin is owner of project:default
        WHEN: Checking admin's editor permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Owners can always edit their projects
        """
        allowed = _check_permission("user:admin", "editor", "project:default")
        assert allowed, "Admin should be editor (via owner inheritance) of project:default"

    def test_bob_cannot_edit_default_project(self):
        """
        GIVEN: Bob only has viewer access to project:default
        WHEN: Checking bob's editor permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot edit projects
        API Endpoint: PUT /api/v1/projects/{id} should fail for bob
        """
        allowed = _check_permission("user:bob", "editor", "project:default")
        assert not allowed, "Bob should NOT be editor of project:default"

    def test_alice_is_owner_of_her_project(self):
        """
        GIVEN: Pre-seeded tuple user:alice owner project:alice_project
        WHEN: Checking alice's owner permission on her project
        THEN: Should return allowed=true

        User Journey: Alice can manage her own project
        """
        allowed = _check_permission("user:alice", "owner", "project:alice_project")
        assert allowed, "Alice should be owner of project:alice_project"


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectViewerAccess:
    """
    Test project viewer authorization from sample-tuples.json.

    Viewers can only read projects.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bob_is_viewer_of_default_project(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer project:default
        WHEN: Checking bob's viewer permission on project:default
        THEN: Should return allowed=true

        User Journey: Bob can view default project
        API Endpoint: GET /api/v1/projects/{id}
        """
        allowed = _check_permission("user:bob", "viewer", "project:default")
        assert allowed, "Bob should be viewer of project:default"

    def test_alice_can_view_via_editor_inheritance(self):
        """
        GIVEN: Alice is editor of project:default
        WHEN: Checking alice's viewer permission (inherited from editor)
        THEN: Should return allowed=true

        User Journey: Editors can always view projects
        """
        allowed = _check_permission("user:alice", "viewer", "project:default")
        assert allowed, "Alice should be viewer (via editor inheritance) of project:default"

    def test_admin_can_view_via_owner_inheritance(self):
        """
        GIVEN: Admin is owner of project:default
        WHEN: Checking admin's viewer permission (inherited from owner)
        THEN: Should return allowed=true

        User Journey: Owners can always view their projects
        """
        allowed = _check_permission("user:admin", "viewer", "project:default")
        assert allowed, "Admin should be viewer (via owner inheritance) of project:default"


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectExecutorAccess:
    """
    Test project executor authorization from sample-tuples.json.

    Executors can run workflows within the project.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_is_executor_of_default_project(self):
        """
        GIVEN: Admin is owner of project:default (executor inherited from owner)
        WHEN: Checking admin's executor permission
        THEN: Should return allowed=true

        User Journey: Admin can run workflows in project
        API Endpoint: POST /api/v1/projects/{id}/workflows/run
        """
        allowed = _check_permission("user:admin", "executor", "project:default")
        assert allowed, "Admin should be executor of project:default"

    def test_alice_can_execute_in_default_project(self):
        """
        GIVEN: Alice has executor access to project:default (via editor or explicit)
        WHEN: Checking alice's executor permission
        THEN: Should return allowed=true

        User Journey: Alice can run workflows in project
        """
        allowed = _check_permission("user:alice", "executor", "project:default")
        assert allowed, "Alice should be executor of project:default"

    def test_bob_cannot_execute_in_default_project(self):
        """
        GIVEN: Bob only has viewer access (no executor)
        WHEN: Checking bob's executor permission
        THEN: Should return allowed=false

        User Journey: Viewers cannot run workflows
        API Endpoint: POST /api/v1/projects/{id}/workflows/run should fail for bob
        """
        allowed = _check_permission("user:bob", "executor", "project:default")
        assert not allowed, "Bob should NOT be executor of project:default"


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectOrganizationAccess:
    """
    Test organization-level project access from sample-tuples.json.

    Organization members can access projects via the organization relation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_acme_org_is_project_organization(self):
        """
        GIVEN: Pre-seeded tuple organization:acme organization project:default
        WHEN: Checking organization relation
        THEN: Should return allowed=true

        User Journey: Projects belong to organizations
        """
        allowed = _check_permission("organization:acme", "organization", "project:default")
        assert allowed, "organization:acme should have organization relation to project:default"


@pytest.mark.xdist_group(name="test_project_authorization")
class TestProjectIsolation:
    """
    Test that users cannot access other users' private projects.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bob_cannot_view_alice_private_project(self):
        """
        GIVEN: Bob has no tuple for project:alice_project
        WHEN: Checking bob's viewer permission on alice's project
        THEN: Should return allowed=false

        User Journey: Private projects are not shared
        """
        allowed = _check_permission("user:bob", "viewer", "project:alice_project")
        assert not allowed, "Bob should NOT be able to view alice's private project"

    def test_alice_cannot_view_admin_private_project(self):
        """
        GIVEN: Alice has no tuple for project:admin_project
        WHEN: Checking alice's viewer permission on admin's project
        THEN: Should return allowed=false

        User Journey: Admin's private projects are isolated
        """
        allowed = _check_permission("user:alice", "viewer", "project:admin_project")
        assert not allowed, "Alice should NOT be able to view admin's private project"

    def test_bob_cannot_edit_any_project(self):
        """
        GIVEN: Bob only has viewer access
        WHEN: Checking bob's editor permission on alice's project
        THEN: Should return allowed=false

        User Journey: Viewers cannot edit any projects
        """
        allowed = _check_permission("user:bob", "editor", "project:alice_project")
        assert not allowed, "Bob should NOT be able to edit alice's project"
