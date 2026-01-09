"""
Integration tests for Skill API Authorization.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that OpenFGA properly enforces authorization for:
1. Skill resources (/admin/skills/*)
2. Skill access levels (admin, author, viewer)
3. Marketplace access (admin, viewer)
4. Skill index access for semantic search

User Journeys:
- Admin: admin of skill:default (full control + author + viewer)
- Alice: author of skill:default (install, uninstall, update + viewer)
- Bob: viewer of skill:default (browse-only)

Reference: sample-tuples.json lines 720-906
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
    pytest.mark.skills,
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


# =============================================================================
# Skill Permission Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillAdminAuthorization:
    """
    Test skill admin authorization from sample-tuples.json.

    Admins have full control over the skill system.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_has_admin_access_to_skill_default(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin skill:default
        WHEN: Checking admin's admin permission on skill:default
        THEN: Should return allowed=true

        User Journey: Admin can manage skill system configuration
        API Endpoint: All /admin/skills/* endpoints
        """
        allowed = _check_permission("user:admin", "admin", "skill:default")
        assert allowed, "Admin should have admin access to skill:default"

    def test_admin_inherits_author_access(self):
        """
        GIVEN: Admin has admin relation to skill:default
        WHEN: Checking admin's author permission (inherited)
        THEN: Should return allowed=true (admin -> author via model)

        User Journey: Admin can install/uninstall/update skills
        API Endpoint: POST /admin/skills/install, DELETE /admin/skills/{name}
        """
        allowed = _check_permission("user:admin", "author", "skill:default")
        assert allowed, "Admin should inherit author access via admin relation"

    def test_admin_inherits_viewer_access(self):
        """
        GIVEN: Admin has admin relation to skill:default
        WHEN: Checking admin's viewer permission (inherited)
        THEN: Should return allowed=true (admin -> author -> viewer via model)

        User Journey: Admin can browse and list skills
        API Endpoint: GET /admin/skills/list, GET /admin/skills/installed
        """
        allowed = _check_permission("user:admin", "viewer", "skill:default")
        assert allowed, "Admin should inherit viewer access via admin relation"


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillAuthorAuthorization:
    """
    Test skill author authorization from sample-tuples.json.

    Authors can install, uninstall, and update skills.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alice_has_author_access_to_skill_default(self):
        """
        GIVEN: Pre-seeded tuple user:alice author skill:default
        WHEN: Checking alice's author permission on skill:default
        THEN: Should return allowed=true

        User Journey: Alice (developer) can install/uninstall/update skills
        API Endpoint: POST /admin/skills/install, DELETE /admin/skills/{name}
        """
        allowed = _check_permission("user:alice", "author", "skill:default")
        assert allowed, "Alice should have author access to skill:default"

    def test_alice_inherits_viewer_access(self):
        """
        GIVEN: Alice has author relation to skill:default
        WHEN: Checking alice's viewer permission (inherited)
        THEN: Should return allowed=true (author -> viewer via model)

        User Journey: Alice can browse and list skills
        API Endpoint: GET /admin/skills/list, GET /admin/skills/installed
        """
        allowed = _check_permission("user:alice", "viewer", "skill:default")
        assert allowed, "Alice should inherit viewer access via author relation"

    def test_alice_cannot_admin_skills(self):
        """
        GIVEN: Alice only has author relation (not admin)
        WHEN: Checking alice's admin permission on skill:default
        THEN: Should return allowed=false

        User Journey: Alice cannot access admin-only skill system features
        """
        allowed = _check_permission("user:alice", "admin", "skill:default")
        assert not allowed, "Alice should NOT have admin access to skill:default"


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillViewerAuthorization:
    """
    Test skill viewer authorization from sample-tuples.json.

    Viewers can browse and list skills (read-only).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bob_has_viewer_access_to_skill_default(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer skill:default
        WHEN: Checking bob's viewer permission on skill:default
        THEN: Should return allowed=true

        User Journey: Bob (basic user) can browse and list skills
        API Endpoint: GET /admin/skills/list, GET /admin/skills/installed
        """
        allowed = _check_permission("user:bob", "viewer", "skill:default")
        assert allowed, "Bob should have viewer access to skill:default"

    def test_bob_cannot_author_skills(self):
        """
        GIVEN: Bob only has viewer relation (not author)
        WHEN: Checking bob's author permission on skill:default
        THEN: Should return allowed=false

        User Journey: Bob cannot install/uninstall skills
        API Endpoint: POST /admin/skills/install should return 403
        """
        allowed = _check_permission("user:bob", "author", "skill:default")
        assert not allowed, "Bob should NOT have author access to skill:default"

    def test_bob_cannot_admin_skills(self):
        """
        GIVEN: Bob only has viewer relation (not admin)
        WHEN: Checking bob's admin permission on skill:default
        THEN: Should return allowed=false

        User Journey: Bob cannot access admin-only skill system features
        """
        allowed = _check_permission("user:bob", "admin", "skill:default")
        assert not allowed, "Bob should NOT have admin access to skill:default"


# =============================================================================
# Marketplace Permission Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestMarketplaceAuthorization:
    """
    Test marketplace authorization from sample-tuples.json.

    Marketplace permissions control access to skill marketplace operations.
    - Admin: can register/manage marketplaces
    - Viewer: can browse listings
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_has_admin_access_to_marketplace(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin marketplace:default
        WHEN: Checking admin's admin permission on marketplace:default
        THEN: Should return allowed=true

        User Journey: Admin can register/manage marketplaces
        API Endpoint: POST /api/v1/marketplaces, DELETE /api/v1/marketplaces/{name}
        """
        allowed = _check_permission("user:admin", "admin", "marketplace:default")
        assert allowed, "Admin should have admin access to marketplace:default"

    def test_admin_inherits_viewer_access_to_marketplace(self):
        """
        GIVEN: Admin has admin relation to marketplace:default
        WHEN: Checking admin's viewer permission (inherited)
        THEN: Should return allowed=true

        User Journey: Admin can browse marketplace listings
        """
        allowed = _check_permission("user:admin", "viewer", "marketplace:default")
        assert allowed, "Admin should inherit viewer access to marketplace"

    def test_alice_has_viewer_access_to_marketplace(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer marketplace:default
        WHEN: Checking alice's viewer permission on marketplace:default
        THEN: Should return allowed=true

        User Journey: Alice can browse marketplace listings
        API Endpoint: GET /admin/skills/list
        """
        allowed = _check_permission("user:alice", "viewer", "marketplace:default")
        assert allowed, "Alice should have viewer access to marketplace:default"

    def test_alice_cannot_admin_marketplace(self):
        """
        GIVEN: Alice only has viewer relation (not admin)
        WHEN: Checking alice's admin permission on marketplace:default
        THEN: Should return allowed=false

        User Journey: Alice cannot register/manage marketplaces
        """
        allowed = _check_permission("user:alice", "admin", "marketplace:default")
        assert not allowed, "Alice should NOT have admin access to marketplace"

    def test_bob_has_viewer_access_to_marketplace(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer marketplace:default
        WHEN: Checking bob's viewer permission on marketplace:default
        THEN: Should return allowed=true

        User Journey: Bob can browse marketplace listings
        """
        allowed = _check_permission("user:bob", "viewer", "marketplace:default")
        assert allowed, "Bob should have viewer access to marketplace:default"

    def test_bob_cannot_admin_marketplace(self):
        """
        GIVEN: Bob only has viewer relation (not admin)
        WHEN: Checking bob's admin permission on marketplace:default
        THEN: Should return allowed=false

        User Journey: Bob cannot register/manage marketplaces
        """
        allowed = _check_permission("user:bob", "admin", "marketplace:default")
        assert not allowed, "Bob should NOT have admin access to marketplace"


# =============================================================================
# Skill Index Permission Tests (Semantic Search)
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillIndexAuthorization:
    """
    Test skill index authorization from sample-tuples.json.

    Skill index permissions control access to semantic skill search.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_has_admin_access_to_skill_index(self):
        """
        GIVEN: Pre-seeded tuple user:admin admin skill_index:default
        WHEN: Checking admin's admin permission on skill_index:default
        THEN: Should return allowed=true

        User Journey: Admin can manage skill search indices
        """
        allowed = _check_permission("user:admin", "admin", "skill_index:default")
        assert allowed, "Admin should have admin access to skill_index:default"

    def test_alice_has_viewer_access_to_skill_index(self):
        """
        GIVEN: Pre-seeded tuple user:alice viewer skill_index:default
        WHEN: Checking alice's viewer permission on skill_index:default
        THEN: Should return allowed=true

        User Journey: Alice can search skills via semantic index
        """
        allowed = _check_permission("user:alice", "viewer", "skill_index:default")
        assert allowed, "Alice should have viewer access to skill_index:default"

    def test_bob_has_viewer_access_to_skill_index(self):
        """
        GIVEN: Pre-seeded tuple user:bob viewer skill_index:default
        WHEN: Checking bob's viewer permission on skill_index:default
        THEN: Should return allowed=true

        User Journey: Bob can search skills via semantic index
        """
        allowed = _check_permission("user:bob", "viewer", "skill_index:default")
        assert allowed, "Bob should have viewer access to skill_index:default"


# =============================================================================
# Negative Permission Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillPermissionDenials:
    """
    Test that unauthorized users are correctly denied access.

    These tests verify the principle of least privilege.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unknown_user_has_no_skill_access(self):
        """
        GIVEN: No tuples exist for user:unknown
        WHEN: Checking unknown user's viewer permission on skill:default
        THEN: Should return allowed=false

        User Journey: Unauthenticated/unknown users cannot access skills
        """
        allowed = _check_permission("user:unknown", "viewer", "skill:default")
        assert not allowed, "Unknown user should have no access to skills"

    def test_unknown_user_has_no_marketplace_access(self):
        """
        GIVEN: No tuples exist for user:unknown
        WHEN: Checking unknown user's viewer permission on marketplace:default
        THEN: Should return allowed=false

        User Journey: Unauthenticated/unknown users cannot browse marketplace
        """
        allowed = _check_permission("user:unknown", "viewer", "marketplace:default")
        assert not allowed, "Unknown user should have no access to marketplace"

    def test_bob_cannot_install_skills(self):
        """
        GIVEN: Bob has viewer relation (not author)
        WHEN: Checking bob's author permission (required for install)
        THEN: Should return allowed=false

        User Journey: Bob clicks "Install" button → API returns 403
        API Endpoint: POST /admin/skills/install
        """
        allowed = _check_permission("user:bob", "author", "skill:default")
        assert not allowed, "Bob should NOT be able to install skills"

    def test_bob_cannot_uninstall_skills(self):
        """
        GIVEN: Bob has viewer relation (not author)
        WHEN: Checking bob's author permission (required for uninstall)
        THEN: Should return allowed=false

        User Journey: Bob tries to uninstall a skill → API returns 403
        API Endpoint: DELETE /admin/skills/{name}
        """
        allowed = _check_permission("user:bob", "author", "skill:default")
        assert not allowed, "Bob should NOT be able to uninstall skills"

    def test_bob_cannot_apply_updates(self):
        """
        GIVEN: Bob has viewer relation (not author)
        WHEN: Checking bob's author permission (required for update apply)
        THEN: Should return allowed=false

        User Journey: Bob tries to apply updates → API returns 403
        API Endpoint: POST /admin/skills/updates/apply
        """
        allowed = _check_permission("user:bob", "author", "skill:default")
        assert not allowed, "Bob should NOT be able to apply skill updates"


# =============================================================================
# Organization-Level Skill Access Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestOrganizationSkillAccess:
    """
    Test organization-level skill access patterns.

    Verifies that organization membership grants appropriate access.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_organization_has_skill_index_access(self):
        """
        GIVEN: Pre-seeded tuple organization:test_org#member viewer skill_index:default
        WHEN: Checking organization member access to skill index
        THEN: Should return allowed=true

        User Journey: All org members can search skills
        """
        allowed = _check_permission("organization:test_org#member", "viewer", "skill_index:default")
        assert allowed, "Organization members should have viewer access to skill_index"
