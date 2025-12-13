"""
ResourceTypeRegistry - Centralized resource type definitions.

Created as part of Phase 3.4 OCP refactoring.

Responsibilities:
- Define supported resource types (tool, conversation, user, etc.)
- Provide validation for resource identifiers
- Enable extensibility for new resource types

Reference: Plan - Phase 3.4 OCP: Authorization Resource Type Registry
"""

from dataclasses import dataclass, field
from enum import Enum


class ResourceType(str, Enum):
    """
    Enumeration of supported authorization resource types.

    Used for type-safe resource type references throughout the codebase.
    """

    TOOL = "tool"
    CONVERSATION = "conversation"
    USER = "user"
    SYSTEM = "system"
    WORKFLOW = "workflow"


@dataclass
class ResourceTypeDefinition:
    """
    Definition of a resource type for authorization.

    Attributes:
        type_name: Resource type identifier (e.g., "tool")
        prefix: Prefix used in resource identifiers (e.g., "tool:")
        allowed_relations: List of valid relations for this type
        description: Human-readable description
    """

    type_name: str
    prefix: str
    allowed_relations: list[str] = field(default_factory=list)
    description: str = ""


class ResourceTypeRegistry:
    """
    Registry for authorization resource types.

    Provides centralized management of resource types, enabling:
    - Validation of resource identifiers
    - Discovery of supported types
    - Extension with custom resource types

    Example:
        >>> registry = ResourceTypeRegistry()
        >>> registry.is_valid_resource("tool:chat")
        True
        >>> registry.get_type_for_resource("conversation:thread1")
        'conversation'
    """

    def __init__(self) -> None:
        """Initialize registry with default resource types."""
        self._types: dict[str, ResourceTypeDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in resource types."""
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.TOOL.value,
                prefix="tool:",
                allowed_relations=["executor", "viewer", "admin"],
                description="AI tools and capabilities",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.CONVERSATION.value,
                prefix="conversation:",
                allowed_relations=["viewer", "editor", "owner"],
                description="Conversation threads and chat sessions",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.USER.value,
                prefix="user:",
                allowed_relations=["self", "viewer", "admin"],
                description="User accounts and profiles",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.SYSTEM.value,
                prefix="system:",
                allowed_relations=["admin", "operator"],
                description="System configuration and administration",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.WORKFLOW.value,
                prefix="workflow:",
                allowed_relations=["executor", "viewer", "editor", "owner"],
                description="LangGraph workflows and pipelines",
            )
        )

    def register(self, definition: ResourceTypeDefinition) -> None:
        """
        Register a resource type definition.

        Args:
            definition: ResourceTypeDefinition to register
        """
        self._types[definition.type_name] = definition

    def get_all_types(self) -> list[str]:
        """
        Get all registered resource type names.

        Returns:
            List of type names
        """
        return list(self._types.keys())

    def get_definition(self, type_name: str) -> ResourceTypeDefinition | None:
        """
        Get definition for a resource type.

        Args:
            type_name: Resource type name

        Returns:
            ResourceTypeDefinition or None if not found
        """
        return self._types.get(type_name)

    def get_type_for_resource(self, resource: str) -> str | None:
        """
        Determine the resource type from a resource identifier.

        Args:
            resource: Resource identifier (e.g., "tool:chat")

        Returns:
            Resource type name or None if unknown
        """
        for type_name, definition in self._types.items():
            if resource.startswith(definition.prefix):
                return type_name
        return None

    def is_valid_resource(self, resource: str) -> bool:
        """
        Check if a resource identifier is valid.

        Args:
            resource: Resource identifier to validate

        Returns:
            True if resource matches a known type
        """
        return self.get_type_for_resource(resource) is not None

    def is_valid_relation_for_type(self, type_name: str, relation: str) -> bool:
        """
        Check if a relation is valid for a resource type.

        Args:
            type_name: Resource type name
            relation: Relation to check

        Returns:
            True if relation is valid for the type
        """
        definition = self._types.get(type_name)
        if definition is None:
            return False
        return relation in definition.allowed_relations

    def get_prefix_for_type(self, type_name: str) -> str | None:
        """
        Get the prefix for a resource type.

        Args:
            type_name: Resource type name

        Returns:
            Prefix string or None if type not found
        """
        definition = self._types.get(type_name)
        return definition.prefix if definition else None


# Global registry instance
_global_registry: ResourceTypeRegistry | None = None


def get_resource_type_registry() -> ResourceTypeRegistry:
    """
    Get the global resource type registry instance.

    Returns:
        ResourceTypeRegistry singleton instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ResourceTypeRegistry()
    return _global_registry


def reset_resource_type_registry() -> None:
    """
    Reset the global resource type registry.

    Useful for testing to ensure clean state.
    """
    global _global_registry
    _global_registry = None
