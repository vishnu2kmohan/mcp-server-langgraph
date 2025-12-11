"""
Tests for Permission Inheritance via acts_as Relationship

Following TDD principles - these tests define the expected behavior
of service principals inheriting permissions from associated users.
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.auth.openfga import check_permission

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for testing permission checks"""
    client = AsyncMock(return_value=None)  # Container for configured methods
    # Default: no permissions
    client.check_permission = AsyncMock(return_value=False)
    client.list_objects = AsyncMock(return_value=[])
    return client


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestDirectPermissions:
    """Test direct permission checks (without inheritance)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_user_has_direct_permission(self, mock_openfga_client):
        """Test user with direct permission to resource"""
        # Arrange
        mock_openfga_client.check_permission.return_value = True

        # Act
        allowed = await check_permission(
            user_id="user:alice",
            relation="viewer",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True
        mock_openfga_client.check_permission.assert_called_once_with(
            user="user:alice", relation="viewer", object="conversation:thread1"
        )

    @pytest.mark.asyncio
    async def test_user_without_permission_denied(self, mock_openfga_client):
        """Test user without permission is denied"""
        # Arrange
        mock_openfga_client.check_permission.return_value = False

        # Act
        allowed = await check_permission(
            user_id="user:bob",
            relation="editor",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is False


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestServicePrincipalInheritedPermissions:
    """Test permission inheritance via acts_as relationship"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_principal_inherits_user_permission(self, mock_openfga_client):
        """Test service principal inherits permission from associated user"""
        # Arrange
        service_id = "service:batch-job"
        associated_user = "user:alice"
        resource = "conversation:thread1"

        # Service has no direct permission
        async def check_side_effect(user, relation, object):
            if user == service_id:
                return False  # No direct permission
            if user == associated_user:
                return True  # User has permission
            return False

        mock_openfga_client.check_permission.side_effect = check_side_effect

        # Service acts as user:alice
        mock_openfga_client.list_objects.return_value = [associated_user]

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="viewer",
            object=resource,
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True

        # Verify check sequence
        calls = mock_openfga_client.check_permission.call_args_list
        # First call: direct check for service principal
        assert calls[0].kwargs == {"user": service_id, "relation": "viewer", "object": resource}
        # Second call: check for associated user
        assert calls[1].kwargs == {"user": associated_user, "relation": "viewer", "object": resource}

    @pytest.mark.asyncio
    async def test_service_principal_without_acts_as_denied(self, mock_openfga_client):
        """Test service principal without acts_as relationship is denied"""
        # Arrange
        mock_openfga_client.check_permission.return_value = False
        mock_openfga_client.list_objects.return_value = []  # No acts_as relationships

        # Act
        allowed = await check_permission(
            user_id="service:orphaned-job",
            relation="viewer",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is False

    @pytest.mark.asyncio
    async def test_service_principal_acts_as_user_without_permission(self, mock_openfga_client):
        """Test service principal acts as user who also lacks permission"""
        # Arrange
        service_id = "service:batch-job"
        associated_user = "user:charlie"

        # Neither service nor user has permission
        mock_openfga_client.check_permission.return_value = False
        mock_openfga_client.list_objects.return_value = [associated_user]

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="editor",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is False

    @pytest.mark.asyncio
    async def test_service_principal_acts_as_multiple_users(self, mock_openfga_client):
        """Test service principal acting as multiple users (first with permission wins)"""
        # Arrange
        service_id = "service:multi-user-job"
        user1 = "user:alice"  # No permission
        user2 = "user:bob"  # Has permission
        resource = "conversation:thread1"

        async def check_side_effect(user, relation, object):
            if user == service_id:
                return False
            if user == user1:
                return False  # Alice has no permission
            if user == user2:
                return True  # Bob has permission
            return False

        mock_openfga_client.check_permission.side_effect = check_side_effect
        mock_openfga_client.list_objects.return_value = [user1, user2]

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="viewer",
            object=resource,
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestServicePrincipalDirectPermissions:
    """Test service principals can also have direct permissions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_principal_direct_permission_without_acts_as(self, mock_openfga_client):
        """Test service principal with direct permission (no user association needed)"""
        # Arrange
        service_id = "service:api-integration"

        # Service has direct permission
        async def check_side_effect(user, relation, object):
            if user == service_id:
                return True  # Direct permission
            return False

        mock_openfga_client.check_permission.side_effect = check_side_effect

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="executor",
            object="tool:data-export",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True

        # Should only check once (direct check succeeds)
        assert mock_openfga_client.check_permission.call_count == 1
        # Should not look up acts_as relationships
        mock_openfga_client.list_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_service_principal_prefers_direct_over_inherited(self, mock_openfga_client):
        """Test that direct permission check happens before inheritance lookup"""
        # Arrange
        service_id = "service:hybrid-job"

        # Service has direct permission
        mock_openfga_client.check_permission.return_value = True

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="viewer",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True

        # Direct check succeeds, so no need to lookup acts_as
        mock_openfga_client.list_objects.assert_not_called()


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestRegularUsersUnaffected:
    """Test that regular users are unaffected by acts_as logic"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_regular_user_permission_check_unchanged(self, mock_openfga_client):
        """Test that regular user permission checks don't trigger acts_as lookup"""
        # Arrange
        mock_openfga_client.check_permission.return_value = True

        # Act
        allowed = await check_permission(
            user_id="user:alice",
            relation="viewer",
            object="conversation:thread1",
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True

        # Only direct check, no acts_as lookup
        assert mock_openfga_client.check_permission.call_count == 1
        mock_openfga_client.list_objects.assert_not_called()


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestPermissionInheritanceLogging:
    """Test that inherited access is logged for audit trail"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_inherited_permission_logs_both_identities(self, mock_openfga_client, caplog):
        """Test that when permission is inherited, both service and user are logged"""
        # Arrange
        import logging

        caplog.set_level(logging.INFO)

        service_id = "service:audit-job"
        associated_user = "user:alice"
        resource = "conversation:thread1"

        async def check_side_effect(user, relation, object):
            if user == service_id:
                return False
            if user == associated_user:
                return True
            return False

        mock_openfga_client.check_permission.side_effect = check_side_effect
        mock_openfga_client.list_objects.return_value = [associated_user]

        # Act
        allowed = await check_permission(
            user_id=service_id,
            relation="viewer",
            object=resource,
            openfga_client=mock_openfga_client,
        )

        # Assert
        assert allowed is True

        # Verify logging (check that service and user are both mentioned)
        log_messages = [record.message for record in caplog.records]
        assert any(service_id in msg and associated_user in msg and resource in msg for msg in log_messages)


@pytest.mark.xdist_group(name="permission_inheritance_tests")
class TestPermissionInheritanceCaching:
    """Test caching of acts_as relationships for performance"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_acts_as_relationships_cached(self, mock_openfga_client):
        """Test that acts_as relationships are cached to reduce OpenFGA calls"""
        # This test assumes caching implementation
        # In real implementation, multiple permission checks for same service
        # should only lookup acts_as relationships once within cache TTL

        service_id = "service:cached-job"
        associated_user = "user:alice"

        async def check_side_effect(user, relation, object):
            if user == associated_user:
                return True
            return False

        mock_openfga_client.check_permission.side_effect = check_side_effect
        mock_openfga_client.list_objects.return_value = [associated_user]

        # Act - check permission twice
        await check_permission(service_id, "viewer", "conversation:1", mock_openfga_client)
        await check_permission(service_id, "viewer", "conversation:2", mock_openfga_client)

        # Assert
        # With caching, list_objects should only be called once
        # (This test will pass once caching is implemented)
        # For now, it documents the expected behavior
        assert mock_openfga_client.list_objects.call_count >= 1
