"""
Unit tests for Partner Access Pattern (Cross-Tenant Sharing).

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 9: Partner access pattern enables secure resource sharing across organizations.

Use cases:
1. Organization A shares a workflow with Organization B's members
2. Time-bound partner access (expires after date)
3. Specific user grants cross-org viewer access to a project

Reference: ADR-0068 Phase 9, Google Zanzibar cross-tenant patterns
"""

import gc
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.auth.authorization import AuthorizationService


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.partner_access,
]


@pytest.fixture
def model_json() -> dict:
    """Load the OpenFGA model for validation."""
    model_path = Path(__file__).parent.parent.parent.parent / "config" / "openfga" / "model.json"
    with open(model_path) as f:
        return json.load(f)


# =============================================================================
# Test: Partner Type Exists in Model
# =============================================================================


@pytest.mark.xdist_group(name="test_partner_access")
class TestPartnerTypeExists:
    """Verify partner type is defined in the model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_partner_type_exists_in_model(self, model_json: dict):
        """
        GIVEN: OpenFGA model
        WHEN: Checking for partner type
        THEN: Partner type should exist with expected relations
        """
        types = {t["type"]: t for t in model_json["type_definitions"]}

        assert "partner" in types, "partner type should exist in model"

    def test_partner_has_source_org_relation(self, model_json: dict):
        """
        GIVEN: OpenFGA model with partner type
        WHEN: Checking partner relations
        THEN: Should have source_org relation
        """
        types = {t["type"]: t for t in model_json["type_definitions"]}
        partner = types.get("partner", {})
        relations = partner.get("relations", {})

        assert "source_org" in relations, "partner should have source_org relation"

    def test_partner_has_target_org_relation(self, model_json: dict):
        """
        GIVEN: OpenFGA model with partner type
        WHEN: Checking partner relations
        THEN: Should have target_org relation
        """
        types = {t["type"]: t for t in model_json["type_definitions"]}
        partner = types.get("partner", {})
        relations = partner.get("relations", {})

        assert "target_org" in relations, "partner should have target_org relation"

    def test_partner_has_admin_relation(self, model_json: dict):
        """
        GIVEN: OpenFGA model with partner type
        WHEN: Checking partner relations
        THEN: Should have admin relation for partnership management
        """
        types = {t["type"]: t for t in model_json["type_definitions"]}
        partner = types.get("partner", {})
        relations = partner.get("relations", {})

        assert "admin" in relations, "partner should have admin relation"

    def test_partner_has_viewer_relation(self, model_json: dict):
        """
        GIVEN: OpenFGA model with partner type
        WHEN: Checking partner relations
        THEN: Should have viewer relation for read access
        """
        types = {t["type"]: t for t in model_json["type_definitions"]}
        partner = types.get("partner", {})
        relations = partner.get("relations", {})

        assert "viewer" in relations, "partner should have viewer relation"


# =============================================================================
# Test: Cross-Tenant Workflow Sharing
# =============================================================================


@pytest.mark.xdist_group(name="test_partner_access")
class TestCrossTenantWorkflowSharing:
    """Test workflow sharing between organizations via partner relationship."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_partner_org_member_can_view_shared_workflow(self):
        """
        GIVEN: Workflow shared with partner organization
        WHEN: Partner org member checks viewer access
        THEN: Should be granted access via partner relationship

        Tuple chain:
        - user:bob -> member -> organization:partner_org
        - organization:partner_org -> target_org -> partner:acme_partner_sharing
        - partner:acme_partner_sharing -> partner -> workflow:shared_workflow
        - workflow.viewer includes partner->target_org->member
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="viewer",
            resource="workflow:shared_workflow",
        )

        # Assert
        assert result is True
        mock_openfga.check_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_partner_org_member_denied_shared_workflow(self):
        """
        GIVEN: Workflow shared only with partner organization
        WHEN: Non-partner org member checks viewer access
        THEN: Should be denied access
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:eve",
            relation="viewer",
            resource="workflow:shared_workflow",
        )

        # Assert
        assert result is False


# =============================================================================
# Test: Cross-Tenant Project Sharing
# =============================================================================


@pytest.mark.xdist_group(name="test_partner_access")
class TestCrossTenantProjectSharing:
    """Test project sharing between organizations via partner relationship."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_partner_org_member_can_view_shared_project(self):
        """
        GIVEN: Project shared with partner organization
        WHEN: Partner org member checks viewer access
        THEN: Should be granted access
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:partner_user",
            relation="viewer",
            resource="project:shared_project",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_partner_cannot_edit_shared_project_by_default(self):
        """
        GIVEN: Project shared with partner organization (viewer only)
        WHEN: Partner org member checks editor access
        THEN: Should be denied (viewer doesn't imply editor)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:partner_user",
            relation="editor",
            resource="project:shared_project",
        )

        # Assert
        assert result is False


# =============================================================================
# Test: Partner Administration
# =============================================================================


@pytest.mark.xdist_group(name="test_partner_access")
class TestPartnerAdministration:
    """Test partner relationship administration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_org_admin_can_create_partner_relationship(self):
        """
        GIVEN: User is admin of source organization
        WHEN: Checking admin access to partner object
        THEN: Should be granted (org admins manage partnerships)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="admin",
            resource="partner:acme_partner_sharing",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_user_cannot_manage_partnerships(self):
        """
        GIVEN: Regular user (not org admin)
        WHEN: Checking admin access to partner object
        THEN: Should be denied
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="admin",
            resource="partner:acme_partner_sharing",
        )

        # Assert
        assert result is False


# =============================================================================
# Test: Time-Bound Partner Access (Condition)
# =============================================================================


@pytest.mark.xdist_group(name="test_partner_access")
class TestTimeBoundPartnerAccess:
    """Test time-bound partner access using conditions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_time_bound_partner_access_granted_within_window(self):
        """
        GIVEN: Partner access with time_bound_share condition
        WHEN: Current time is before expiry
        THEN: Access should be granted
        """
        # Arrange - OpenFGA evaluates condition, returns True if within window
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:temp_partner",
            relation="viewer",
            resource="workflow:temp_shared",
            context={"current_time": "2026-01-08T12:00:00Z"},
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_time_bound_partner_access_denied_after_expiry(self):
        """
        GIVEN: Partner access with time_bound_share condition
        WHEN: Current time is after expiry
        THEN: Access should be denied
        """
        # Arrange - OpenFGA evaluates condition, returns False if expired
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:temp_partner",
            relation="viewer",
            resource="workflow:temp_shared",
            context={"current_time": "2027-01-08T12:00:00Z"},
        )

        # Assert
        assert result is False
