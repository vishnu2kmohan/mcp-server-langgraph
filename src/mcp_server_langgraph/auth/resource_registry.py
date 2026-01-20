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
    Aligned with OpenFGA model.json (33 types).
    """

    # Core types
    USER = "user"
    ORGANIZATION = "organization"
    ROLE = "role"
    SYSTEM = "system"

    # Resource types
    TOOL = "tool"
    CONVERSATION = "conversation"
    WORKFLOW = "workflow"
    SESSION = "session"
    PROJECT = "project"
    CHAT = "chat"

    # Infrastructure types
    SERVICE_PRINCIPAL = "service_principal"
    API_KEY = "api_key"
    GATEWAY = "gateway"
    MCP = "mcp"
    MCP_CONNECTION = "mcp_connection"
    CONNECTION = "connection"

    # Data types
    VECTOR_STORE = "vector_store"

    # Authorization & Observability
    AUTHZ = "authz"
    DASHBOARD = "dashboard"
    COST = "cost"
    OBSERVABILITY = "observability"
    LOGS = "logs"
    TRACES = "traces"
    METRICS = "metrics"
    IDENTITY = "identity"
    BUDGET = "budget"

    # AI & Agents
    AI = "ai"
    AGENT = "agent"
    SKILL = "skill"
    EXECUTION = "execution"

    # Compliance & Admin
    COMPLIANCE = "compliance"
    MARKETPLACE = "marketplace"
    CONFIG = "config"

    # References
    REFERENCE = "reference"

    # Memory and Plans (Phase 4 references)
    MEMORY = "memory"
    PLAN = "plan"


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
        """Register built-in resource types aligned with OpenFGA model.json."""
        # ========== Core Types ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.USER.value,
                prefix="user:",
                allowed_relations=[],  # Base type, no relations
                description="User accounts and profiles",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.ORGANIZATION.value,
                prefix="organization:",
                allowed_relations=["admin", "member"],
                description="Organizations and teams",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.ROLE.value,
                prefix="role:",
                allowed_relations=["assignee"],
                description="Role assignments for sub-personas",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.SYSTEM.value,
                prefix="system:",
                allowed_relations=["admin", "developer", "user", "viewer"],
                description="System-level global access for sub-personas",
            )
        )

        # ========== Resource Types ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.TOOL.value,
                prefix="tool:",
                allowed_relations=["executor", "organization", "owner"],
                description="AI tools and capabilities",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.CONVERSATION.value,
                prefix="conversation:",
                allowed_relations=["editor", "owner", "viewer"],
                description="Conversation threads and chat sessions",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.WORKFLOW.value,
                prefix="workflow:",
                allowed_relations=["editor", "executor", "organization", "owner", "project", "viewer"],
                description="LangGraph workflows and pipelines",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.SESSION.value,
                prefix="session:",
                allowed_relations=["editor", "organization", "owner", "project", "viewer"],
                description="User sessions",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.PROJECT.value,
                prefix="project:",
                allowed_relations=["editor", "executor", "organization", "owner", "viewer"],
                description="Projects",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.CHAT.value,
                prefix="chat:",
                allowed_relations=["organization", "owner", "viewer"],
                description="Chat conversations",
            )
        )

        # ========== Infrastructure Types ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.SERVICE_PRINCIPAL.value,
                prefix="service_principal:",
                allowed_relations=["acts_as", "editor", "owner", "viewer"],
                description="Service accounts and principals",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.API_KEY.value,
                prefix="api_key:",
                allowed_relations=["owner", "revoker", "viewer"],
                description="API keys",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.GATEWAY.value,
                prefix="gateway:",
                allowed_relations=["admin", "viewer"],
                description="Gateway access",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.MCP.value,
                prefix="mcp:",
                allowed_relations=["user", "viewer"],
                description="MCP server access",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.MCP_CONNECTION.value,
                prefix="mcp_connection:",
                allowed_relations=["owner", "viewer"],
                description="MCP connections",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.CONNECTION.value,
                prefix="connection:",
                allowed_relations=["organization", "owner", "viewer"],
                description="MCP connections and integrations",
            )
        )

        # ========== Data Types ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.VECTOR_STORE.value,
                prefix="vector_store:",
                allowed_relations=["editor", "organization", "owner", "viewer"],
                description="Vector store collections",
            )
        )

        # ========== Authorization & Observability ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.AUTHZ.value,
                prefix="authz:",
                allowed_relations=["admin", "viewer"],
                description="Authorization management",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.DASHBOARD.value,
                prefix="dashboard:",
                allowed_relations=["admin", "editor", "organization", "viewer"],
                description="Dashboards",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.COST.value,
                prefix="cost:",
                allowed_relations=["admin", "organization", "viewer"],
                description="Cost tracking",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.OBSERVABILITY.value,
                prefix="observability:",
                allowed_relations=["admin", "organization", "viewer"],
                description="Observability metrics",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.LOGS.value,
                prefix="logs:",
                allowed_relations=["admin", "viewer"],
                description="Audit logs",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.TRACES.value,
                prefix="traces:",
                allowed_relations=["admin", "viewer"],
                description="Distributed traces",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.METRICS.value,
                prefix="metrics:",
                allowed_relations=["admin", "viewer"],
                description="System metrics",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.IDENTITY.value,
                prefix="identity:",
                allowed_relations=["admin", "viewer"],
                description="Identity providers",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.BUDGET.value,
                prefix="budget:",
                allowed_relations=["admin", "organization", "viewer"],
                description="Budget alerts and cost limits",
            )
        )

        # ========== AI & Agents ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.AI.value,
                prefix="ai:",
                allowed_relations=["admin", "user", "viewer"],
                description="AI features and suggestions",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.AGENT.value,
                prefix="agent:",
                allowed_relations=["admin", "organization", "owner", "viewer"],
                description="Agent configuration and HITL operations",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.SKILL.value,
                prefix="skill:",
                allowed_relations=["admin", "viewer"],
                description="Skill management operations",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.EXECUTION.value,
                prefix="execution:",
                allowed_relations=["organization", "owner", "viewer"],
                description="Workflow execution tracking",
            )
        )

        # ========== Compliance & Admin ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.COMPLIANCE.value,
                prefix="compliance:",
                allowed_relations=["admin", "viewer"],
                description="Compliance reports (GDPR, HIPAA, SOC2, FedRAMP)",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.MARKETPLACE.value,
                prefix="marketplace:",
                allowed_relations=["admin"],
                description="Marketplace admin operations",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.CONFIG.value,
                prefix="config:",
                allowed_relations=["admin", "viewer"],
                description="System configuration",
            )
        )

        # ========== References ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.REFERENCE.value,
                prefix="reference:",
                allowed_relations=["viewer"],
                description="Markdown reference resolution",
            )
        )

        # ========== Memory and Plans (Phase 4 References) ==========
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.MEMORY.value,
                prefix="memory:",
                allowed_relations=["session", "viewer"],
                description="Memory notes for [[memory:id]] markdown references",
            )
        )
        self.register(
            ResourceTypeDefinition(
                type_name=ResourceType.PLAN.value,
                prefix="plan:",
                allowed_relations=["session", "viewer"],
                description="Execution plans for [[plan:id]] markdown references",
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
