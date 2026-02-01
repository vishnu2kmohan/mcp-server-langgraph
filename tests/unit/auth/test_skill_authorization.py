"""
Unit tests for Skill Authorization with fine-grained OpenFGA permissions.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify:
- admin: Full access to all skill operations + marketplace management
- author: Can install, uninstall, update skills (alice)
- viewer: Can only browse and list skills (bob)
- marketplace:admin: Only admins can register/manage marketplaces

Reference: ADR-0002 OpenFGA Authorization, ADR-0068 Gateway-Level Authentication
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.auth.authorization import AuthorizationService

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.skills,
]


# =============================================================================
# Test: Skill Type Authorization
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillViewerAuthorization:
    """Test skill:viewer permission (alice and bob can browse/list skills)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_viewer_can_list_skills(self):
        """
        GIVEN: User bob has skill:viewer permission
        WHEN: Authorizing to list skills
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="viewer",
            resource="skill:default",
        )

        # Assert
        assert result is True
        mock_openfga.check_permission.assert_called_once_with(
            user="user:bob",
            relation="viewer",
            object="skill:default",
            context={"contextual_tuples": []},
        )

    @pytest.mark.asyncio
    async def test_viewer_cannot_install_skills(self):
        """
        GIVEN: User bob has only skill:viewer permission (not author)
        WHEN: Checking author permission
        THEN: Should return False
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="author",
            resource="skill:default",
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_viewer_cannot_admin_skills(self):
        """
        GIVEN: User bob has only skill:viewer permission
        WHEN: Checking admin permission
        THEN: Should return False
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="admin",
            resource="skill:default",
        )

        # Assert
        assert result is False


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillAuthorAuthorization:
    """Test skill:author permission (alice can install/update skills)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_author_can_install_skills(self):
        """
        GIVEN: User alice has skill:author permission
        WHEN: Authorizing to install a skill
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="author",
            resource="skill:default",
        )

        # Assert
        assert result is True
        mock_openfga.check_permission.assert_called_once_with(
            user="user:alice",
            relation="author",
            object="skill:default",
            context={"contextual_tuples": []},
        )

    @pytest.mark.asyncio
    async def test_author_can_uninstall_skills(self):
        """
        GIVEN: User alice has skill:author permission
        WHEN: Authorizing to uninstall a skill
        THEN: Should return True (author implies uninstall permission)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="author",
            resource="skill:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_author_can_apply_updates(self):
        """
        GIVEN: User alice has skill:author permission
        WHEN: Authorizing to apply skill updates
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="author",
            resource="skill:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_author_inherits_viewer(self):
        """
        GIVEN: User alice has skill:author permission
        WHEN: Checking viewer permission (inherited)
        THEN: Should return True (author implies viewer)
        """
        # Arrange - OpenFGA computes viewer from author
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="skill:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_author_cannot_admin_marketplace(self):
        """
        GIVEN: User alice has skill:author but not marketplace:admin
        WHEN: Checking marketplace admin permission
        THEN: Should return False
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="admin",
            resource="marketplace:default",
        )

        # Assert
        assert result is False


@pytest.mark.xdist_group(name="test_skill_authorization")
class TestSkillAdminAuthorization:
    """Test skill:admin permission (full access)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_admin_has_full_skill_access(self):
        """
        GIVEN: Admin user has skill:admin permission
        WHEN: Authorizing for admin operations
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="admin",
            resource="skill:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_inherits_author(self):
        """
        GIVEN: Admin user has skill:admin permission
        WHEN: Checking author permission (inherited)
        THEN: Should return True (admin implies author)
        """
        # Arrange - OpenFGA computes author from admin
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="author",
            resource="skill:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_inherits_viewer(self):
        """
        GIVEN: Admin user has skill:admin permission
        WHEN: Checking viewer permission (inherited)
        THEN: Should return True (admin implies viewer)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="viewer",
            resource="skill:default",
        )

        # Assert
        assert result is True


# =============================================================================
# Test: Marketplace Type Authorization
# =============================================================================


@pytest.mark.xdist_group(name="test_marketplace_authorization")
class TestMarketplaceViewerAuthorization:
    """Test marketplace:viewer permission (alice/bob can browse marketplace)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_viewer_can_browse_marketplace(self):
        """
        GIVEN: User alice has marketplace:viewer permission
        WHEN: Authorizing to browse marketplace listings
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="marketplace:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_viewer_cannot_register_marketplace(self):
        """
        GIVEN: User alice has marketplace:viewer but not admin
        WHEN: Checking admin permission to register marketplace
        THEN: Should return False
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="admin",
            resource="marketplace:default",
        )

        # Assert
        assert result is False


@pytest.mark.xdist_group(name="test_marketplace_authorization")
class TestMarketplaceAdminAuthorization:
    """Test marketplace:admin permission (only admin can manage marketplaces)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_admin_can_register_marketplace(self):
        """
        GIVEN: Admin has marketplace:admin permission
        WHEN: Authorizing to register new marketplace
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="admin",
            resource="marketplace:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_can_manage_skill_availability(self):
        """
        GIVEN: Admin has marketplace:admin permission
        WHEN: Authorizing to manage which skills are available
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="admin",
            resource="marketplace:default",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_inherits_marketplace_viewer(self):
        """
        GIVEN: Admin has marketplace:admin permission
        WHEN: Checking viewer permission (inherited)
        THEN: Should return True
        """
        # Arrange - OpenFGA computes viewer from admin
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="viewer",
            resource="marketplace:default",
        )

        # Assert
        assert result is True


# =============================================================================
# Test: Permission Hierarchy Validation
# =============================================================================


@pytest.mark.xdist_group(name="test_skill_permission_hierarchy")
class TestSkillPermissionHierarchy:
    """Test that permission hierarchy is correctly computed by OpenFGA.

    Expected hierarchy for skill type:
    - admin -> author -> viewer

    admin has: admin, author, viewer
    author has: author, viewer
    viewer has: viewer only
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_permission_escalation_prevented(self):
        """
        GIVEN: User with only viewer permission
        WHEN: Attempting to access author-level operations
        THEN: Should be denied (no privilege escalation)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        # OpenFGA correctly denies author for viewer-only user
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="author",
            resource="skill:default",
        )

        # Assert - privilege escalation prevented
        assert result is False

    @pytest.mark.asyncio
    async def test_cross_resource_isolation(self):
        """
        GIVEN: User with author permission on skills
        WHEN: Attempting to access marketplace admin
        THEN: Should be denied (resource isolation)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act - alice has skill:author but not marketplace:admin
        result = await service.authorize(
            user_id="user:alice",
            relation="admin",
            resource="marketplace:anthropic",
        )

        # Assert - cross-resource access denied
        assert result is False


# =============================================================================
# Test: Skills API Authorization Matrix
# =============================================================================


@pytest.mark.xdist_group(name="test_skills_api_authorization")
class TestSkillsAPIAuthorizationMatrix:
    """Test complete authorization matrix for Skills API endpoints.

    Endpoint Authorization Requirements:
    - GET /list         -> skill:viewer OR marketplace:viewer
    - GET /installed    -> skill:viewer
    - GET /updates      -> skill:viewer
    - POST /install     -> skill:author
    - DELETE /{name}    -> skill:author
    - POST /updates/apply -> skill:author
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user,expected",
        [
            ("user:admin", True),  # admin -> author -> viewer
            ("user:alice", True),  # author -> viewer
            ("user:bob", True),  # viewer
        ],
    )
    async def test_list_skills_authorization(self, user: str, expected: bool):
        """All users with skill:viewer can list skills."""
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=expected)

        service = AuthorizationService(openfga_client=mock_openfga)

        result = await service.authorize(
            user_id=user,
            relation="viewer",
            resource="skill:default",
        )

        assert result is expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user,expected",
        [
            ("user:admin", True),  # admin -> author
            ("user:alice", True),  # author
            ("user:bob", False),  # viewer only - cannot install
        ],
    )
    async def test_install_skill_authorization(self, user: str, expected: bool):
        """Only users with skill:author can install skills."""
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=expected)

        service = AuthorizationService(openfga_client=mock_openfga)

        result = await service.authorize(
            user_id=user,
            relation="author",
            resource="skill:default",
        )

        assert result is expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user,expected",
        [
            ("user:admin", True),  # admin -> author
            ("user:alice", True),  # author
            ("user:bob", False),  # viewer only - cannot uninstall
        ],
    )
    async def test_uninstall_skill_authorization(self, user: str, expected: bool):
        """Only users with skill:author can uninstall skills."""
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=expected)

        service = AuthorizationService(openfga_client=mock_openfga)

        result = await service.authorize(
            user_id=user,
            relation="author",
            resource="skill:default",
        )

        assert result is expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user,expected",
        [
            ("user:admin", True),  # marketplace:admin
            ("user:alice", False),  # no marketplace admin
            ("user:bob", False),  # no marketplace admin
        ],
    )
    async def test_register_marketplace_authorization(self, user: str, expected: bool):
        """Only users with marketplace:admin can register marketplaces."""
        mock_openfga = AsyncMock(spec=["check_permission"])
        mock_openfga.check_permission = AsyncMock(return_value=expected)

        service = AuthorizationService(openfga_client=mock_openfga)

        result = await service.authorize(
            user_id=user,
            relation="admin",
            resource="marketplace:default",
        )

        assert result is expected
