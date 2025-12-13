"""
MockResourceGenerator - Development/testing mock data.

Extracted from AuthMiddleware as part of Phase 2.1 SRP decomposition.

Responsibilities:
- Generate mock resources for development/testing
- Scope resources by user for proper RBAC semantics

Reference: Plan - Phase 2.1 SRP: Decompose AuthMiddleware
"""


class MockResourceGenerator:
    """
    Generator for mock resources in development/testing.

    Provides sample data when OpenFGA is not available, enabling
    development and testing without authorization infrastructure.

    Resources are scoped per user to maintain proper RBAC semantics.
    """

    # Standard mock tools available in development
    DEFAULT_MOCK_TOOLS: list[str] = [
        "tool:agent_chat",
        "tool:conversation_get",
        "tool:conversation_search",
    ]

    # Standard mock users for development
    DEFAULT_MOCK_USERS: list[str] = [
        "user:alice",
        "user:bob",
        "user:charlie",
    ]

    # Template for user-scoped conversations
    CONVERSATION_TEMPLATES: list[str] = [
        "conversation:{username}_demo_thread_1",
        "conversation:{username}_demo_thread_2",
        "conversation:{username}_demo_thread_3",
        "conversation:{username}_sample_conversation",
    ]

    def __init__(
        self,
        mock_tools: list[str] | None = None,
        mock_users: list[str] | None = None,
        conversation_templates: list[str] | None = None,
    ):
        """
        Initialize MockResourceGenerator.

        Args:
            mock_tools: Custom list of mock tools (optional)
            mock_users: Custom list of mock users (optional)
            conversation_templates: Custom conversation templates (optional)
        """
        self._mock_tools = mock_tools or self.DEFAULT_MOCK_TOOLS
        self._mock_users = mock_users or self.DEFAULT_MOCK_USERS
        self._conversation_templates = conversation_templates or self.CONVERSATION_TEMPLATES

    def get_resources(
        self,
        user_id: str,
        relation: str,  # noqa: ARG002 (reserved for future use)
        resource_type: str,
    ) -> list[str]:
        """
        Get mock resources for development/testing.

        Provides sample data to enable development and testing without
        authorization infrastructure. Resources are scoped per user to
        maintain proper RBAC semantics.

        Args:
            user_id: User identifier (used to scope conversation resources)
            relation: Relation to check (reserved for future filtering)
            resource_type: Type of resources (e.g., "tool", "conversation")

        Returns:
            List of mock resource identifiers scoped to the user
        """
        # Extract username from user_id
        username = self._extract_username(user_id)

        # Return resources based on type
        if resource_type == "tool":
            return self._mock_tools.copy()

        if resource_type == "conversation":
            return self._get_user_conversations(username)

        if resource_type == "user":
            return self._mock_users.copy()

        # Unknown resource type returns empty list
        return []

    def _extract_username(self, user_id: str) -> str:
        """Extract username from user_id, handling various formats."""
        if ":" in user_id:
            return user_id.split(":")[-1]
        return user_id

    def _get_user_conversations(self, username: str) -> list[str]:
        """Get user-scoped conversation resources."""
        return [template.format(username=username) for template in self._conversation_templates]
