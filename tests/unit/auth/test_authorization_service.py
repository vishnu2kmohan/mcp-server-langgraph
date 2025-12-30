"""
Unit tests for AuthorizationService extracted from AuthMiddleware.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.1 SRP decomposition - Testing authorization logic separately
from authentication and session management.

Reference: Plan - Phase 2.1 SRP: Decompose AuthMiddleware
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.auth.authorization import AuthorizationService


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.mark.xdist_group(name="test_authorization_service")
class TestAuthorizationServiceOpenFGA:
    """Test AuthorizationService with OpenFGA integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_granted(self):
        """
        GIVEN: OpenFGA client that grants permission
        WHEN: Authorizing user for resource
        THEN: Should return True
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
        )

        # Assert
        assert result is True
        mock_openfga.check_permission.assert_called_once_with(
            user="user:alice",
            relation="executor",
            object="tool:chat",
            context=None,
        )

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_denied(self):
        """
        GIVEN: OpenFGA client that denies permission
        WHEN: Authorizing user for resource
        THEN: Should return False
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=False)

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:bob",
            relation="admin",
            resource="system:config",
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_openfga_error_fails_closed(self):
        """
        GIVEN: OpenFGA client that raises exception
        WHEN: Authorizing user for resource
        THEN: Should return False (fail closed)
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(side_effect=Exception("Connection error"))

        service = AuthorizationService(openfga_client=mock_openfga)

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
        )

        # Assert - fail closed
        assert result is False


@pytest.mark.xdist_group(name="test_authorization_service")
class TestAuthorizationServiceFallback:
    """Test fallback authorization when OpenFGA unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fallback_denied_in_production(self):
        """
        GIVEN: No OpenFGA and production environment
        WHEN: Authorizing user
        THEN: Should deny access (security control)
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.allow_auth_fallback = True  # Even if enabled

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
        )

        # Assert - denied in production
        assert result is False

    @pytest.mark.asyncio
    async def test_fallback_denied_when_not_enabled(self):
        """
        GIVEN: No OpenFGA and fallback not enabled
        WHEN: Authorizing user
        THEN: Should deny access
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.allow_auth_fallback = False

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_fallback_admin_role_granted(self):
        """
        GIVEN: Fallback enabled and admin user
        WHEN: Authorizing for any resource
        THEN: Should grant access
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        mock_user_provider = AsyncMock(spec=["get_user_by_username"])  # async-mock-configured
        mock_user_data = MagicMock()
        mock_user_data.roles = ["admin"]
        mock_user_provider.get_user_by_username = AsyncMock(return_value=mock_user_data)

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
            user_provider=mock_user_provider,
        )

        # Act
        result = await service.authorize(
            user_id="user:admin",
            relation="admin",
            resource="system:config",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_tool_executor_role_granted(self):
        """
        GIVEN: Fallback enabled and user with user role
        WHEN: Authorizing for tool executor
        THEN: Should grant access
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        mock_user_provider = AsyncMock(spec=["get_user_by_username"])  # async-mock-configured
        mock_user_data = MagicMock()
        mock_user_data.roles = ["user"]
        mock_user_provider.get_user_by_username = AsyncMock(return_value=mock_user_data)

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
            user_provider=mock_user_provider,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_conversation_own_access_granted(self):
        """
        GIVEN: Fallback enabled and user accessing own conversation
        WHEN: Authorizing for viewer relation
        THEN: Should grant access
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        mock_user_provider = AsyncMock(spec=["get_user_by_username"])  # async-mock-configured
        mock_user_data = MagicMock()
        mock_user_data.roles = ["user"]
        mock_user_provider.get_user_by_username = AsyncMock(return_value=mock_user_data)

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
            user_provider=mock_user_provider,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="conversation:alice_thread_1",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_conversation_other_user_denied(self):
        """
        GIVEN: Fallback enabled and user accessing other's conversation
        WHEN: Authorizing for viewer relation
        THEN: Should deny access
        """
        # Arrange
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        mock_user_provider = AsyncMock(spec=["get_user_by_username"])  # async-mock-configured
        mock_user_data = MagicMock()
        mock_user_data.roles = ["user"]
        mock_user_provider.get_user_by_username = AsyncMock(return_value=mock_user_data)

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
            user_provider=mock_user_provider,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="conversation:bob_private_thread",
        )

        # Assert - denied (not alice's conversation)
        assert result is False


@pytest.mark.xdist_group(name="test_authorization_service")
class TestAuthorizationServiceWithContext:
    """Test AuthorizationService context passing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_passes_context_to_openfga(self):
        """
        GIVEN: Authorization request with context
        WHEN: Calling authorize
        THEN: Context should be passed to OpenFGA
        """
        # Arrange
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(openfga_client=mock_openfga)

        context = {"request_id": "req-123", "ip_address": "192.168.1.1"}

        # Act
        await service.authorize(
            user_id="user:alice",
            relation="executor",
            resource="tool:chat",
            context=context,
        )

        # Assert
        mock_openfga.check_permission.assert_called_once_with(
            user="user:alice",
            relation="executor",
            object="tool:chat",
            context=context,
        )


@pytest.mark.xdist_group(name="test_authorization_service")
class TestAuthorizationServiceWithResourceRegistry:
    """Test AuthorizationService with ResourceTypeRegistry integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        # Reset the global resource registry
        from mcp_server_langgraph.auth.resource_registry import reset_resource_type_registry

        reset_resource_type_registry()

    @pytest.mark.asyncio
    async def test_authorize_validates_resource_type(self):
        """
        GIVEN: AuthorizationService with resource registry
        WHEN: Authorizing with unknown resource type
        THEN: Should deny access (invalid resource type)
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.allow_auth_fallback = True

        service = AuthorizationService(
            openfga_client=None,
            settings=mock_settings,
            resource_registry=registry,
        )

        # Act
        result = await service.authorize(
            user_id="user:alice",
            relation="viewer",
            resource="unknown:resource",  # Unknown resource type
        )

        # Assert - denied due to invalid resource type
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_validates_relation_for_type(self):
        """
        GIVEN: AuthorizationService with resource registry
        WHEN: Authorizing with invalid relation for resource type
        THEN: Should deny access (invalid relation)
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(
            openfga_client=mock_openfga,
            resource_registry=registry,
        )

        # Act - try "admin" relation on "tool" type (not allowed)
        # Tool type only allows: executor, organization, owner
        result = await service.authorize(
            user_id="user:alice",
            relation="admin",  # "admin" is not a valid relation for "tool"
            resource="tool:chat",
        )

        # Assert - denied due to invalid relation for type
        assert result is False
        # OpenFGA should not even be called
        mock_openfga.check_permission.assert_not_called()

    @pytest.mark.asyncio
    async def test_authorize_with_valid_resource_and_relation_proceeds(self):
        """
        GIVEN: AuthorizationService with resource registry
        WHEN: Authorizing with valid resource type and relation
        THEN: Should proceed to OpenFGA check
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(
            openfga_client=mock_openfga,
            resource_registry=registry,
        )

        # Act - valid relation for tool type
        result = await service.authorize(
            user_id="user:alice",
            relation="executor",  # "executor" is valid for "tool"
            resource="tool:chat",
        )

        # Assert - proceeds to OpenFGA
        assert result is True
        mock_openfga.check_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorize_without_registry_skips_validation(self):
        """
        GIVEN: AuthorizationService without resource registry
        WHEN: Authorizing any resource
        THEN: Should proceed without resource/relation validation
        """
        # Arrange - no registry provided
        mock_openfga = AsyncMock(spec=["check_permission"])  # async-mock-configured
        mock_openfga.check_permission = AsyncMock(return_value=True)

        service = AuthorizationService(
            openfga_client=mock_openfga,
            resource_registry=None,
        )

        # Act - even unknown types should proceed to OpenFGA
        result = await service.authorize(
            user_id="user:alice",
            relation="custom_relation",
            resource="custom:resource",
        )

        # Assert - proceeds to OpenFGA (backward compatible)
        assert result is True
        mock_openfga.check_permission.assert_called_once()
