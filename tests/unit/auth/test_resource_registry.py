"""
Unit tests for ResourceTypeRegistry.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 3.4 OCP - Testing resource type registry for extensibility.

Reference: Plan - Phase 3.4 OCP: Authorization Resource Type Registry
"""

import gc

import pytest


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.mark.xdist_group(name="test_resource_registry")
class TestResourceTypeRegistry:
    """Test ResourceTypeRegistry for resource type management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        # Reset global registry
        from mcp_server_langgraph.auth.resource_registry import reset_resource_type_registry

        reset_resource_type_registry()

    def test_registry_has_default_types(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting all types
        THEN: Should include default types (tool, conversation, user)
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act
        types = registry.get_all_types()

        # Assert
        assert "tool" in types
        assert "conversation" in types
        assert "user" in types

    def test_get_type_for_tool_resource(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting type for tool resource
        THEN: Should return 'tool'
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act
        resource_type = registry.get_type_for_resource("tool:chat")

        # Assert
        assert resource_type == "tool"

    def test_get_type_for_conversation_resource(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting type for conversation resource
        THEN: Should return 'conversation'
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act
        resource_type = registry.get_type_for_resource("conversation:thread1")

        # Assert
        assert resource_type == "conversation"

    def test_get_type_for_unknown_resource(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting type for unknown resource
        THEN: Should return None
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act
        resource_type = registry.get_type_for_resource("unknown:resource")

        # Assert
        assert resource_type is None

    def test_is_valid_resource_returns_true_for_known_type(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Validating known resource
        THEN: Should return True
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act & Assert
        assert registry.is_valid_resource("tool:chat") is True
        assert registry.is_valid_resource("conversation:thread1") is True
        assert registry.is_valid_resource("user:alice") is True

    def test_is_valid_resource_returns_false_for_unknown_type(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Validating unknown resource
        THEN: Should return False
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act & Assert
        assert registry.is_valid_resource("unknown:resource") is False
        assert registry.is_valid_resource("invalid") is False

    def test_is_valid_relation_for_type(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Checking relation validity for type
        THEN: Should return True for valid relations
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act & Assert
        assert registry.is_valid_relation_for_type("tool", "executor") is True
        assert registry.is_valid_relation_for_type("conversation", "viewer") is True
        assert registry.is_valid_relation_for_type("conversation", "editor") is True

    def test_is_valid_relation_returns_false_for_invalid_relation(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Checking invalid relation for type
        THEN: Should return False
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act & Assert
        assert registry.is_valid_relation_for_type("tool", "owner") is False
        assert registry.is_valid_relation_for_type("unknown_type", "viewer") is False


@pytest.mark.xdist_group(name="test_resource_registry")
class TestResourceTypeRegistryExtensibility:
    """Test ResourceTypeRegistry extensibility features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.auth.resource_registry import reset_resource_type_registry

        reset_resource_type_registry()

    def test_register_custom_resource_type(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Registering a custom resource type
        THEN: Should be available for lookup
        """
        from mcp_server_langgraph.auth.resource_registry import (
            ResourceTypeDefinition,
            ResourceTypeRegistry,
        )

        # Arrange
        registry = ResourceTypeRegistry()
        custom_type = ResourceTypeDefinition(
            type_name="document",
            prefix="document:",
            allowed_relations=["reader", "editor", "owner"],
            description="Document resources",
        )

        # Act
        registry.register(custom_type)

        # Assert
        assert "document" in registry.get_all_types()
        assert registry.get_type_for_resource("document:123") == "document"
        assert registry.is_valid_relation_for_type("document", "reader") is True

    def test_get_prefix_for_type(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting prefix for type
        THEN: Should return correct prefix
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act & Assert
        assert registry.get_prefix_for_type("tool") == "tool:"
        assert registry.get_prefix_for_type("conversation") == "conversation:"
        assert registry.get_prefix_for_type("unknown") is None

    def test_get_definition_returns_full_definition(self):
        """
        GIVEN: ResourceTypeRegistry instance
        WHEN: Getting definition for type
        THEN: Should return complete ResourceTypeDefinition
        """
        from mcp_server_langgraph.auth.resource_registry import ResourceTypeRegistry

        # Arrange
        registry = ResourceTypeRegistry()

        # Act
        definition = registry.get_definition("tool")

        # Assert
        assert definition is not None
        assert definition.type_name == "tool"
        assert definition.prefix == "tool:"
        assert "executor" in definition.allowed_relations


@pytest.mark.xdist_group(name="test_resource_registry")
class TestResourceTypeRegistryGlobalInstance:
    """Test global registry instance management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.auth.resource_registry import reset_resource_type_registry

        reset_resource_type_registry()

    def test_get_global_registry_returns_singleton(self):
        """
        GIVEN: Multiple calls to get_resource_type_registry
        WHEN: Getting the global registry
        THEN: Should return the same instance
        """
        from mcp_server_langgraph.auth.resource_registry import get_resource_type_registry

        # Act
        registry1 = get_resource_type_registry()
        registry2 = get_resource_type_registry()

        # Assert
        assert registry1 is registry2

    def test_reset_registry_creates_new_instance(self):
        """
        GIVEN: Global registry instance
        WHEN: Resetting the registry
        THEN: Next call should return new instance
        """
        from mcp_server_langgraph.auth.resource_registry import (
            get_resource_type_registry,
            reset_resource_type_registry,
        )

        # Arrange
        registry1 = get_resource_type_registry()

        # Act
        reset_resource_type_registry()
        registry2 = get_resource_type_registry()

        # Assert
        assert registry1 is not registry2
