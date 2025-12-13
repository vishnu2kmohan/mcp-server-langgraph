"""
Unit tests for MockResourceGenerator extracted from AuthMiddleware.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.1 SRP decomposition - Testing mock resource generation separately
from authentication and authorization logic.

Reference: Plan - Phase 2.1 SRP: Decompose AuthMiddleware
"""

import gc

import pytest

from mcp_server_langgraph.auth.mock_resources import MockResourceGenerator


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.mark.xdist_group(name="test_mock_resources")
class TestMockResourceGenerator:
    """Test MockResourceGenerator for development/testing scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_mock_tools(self):
        """
        GIVEN: MockResourceGenerator
        WHEN: Requesting tool resources
        THEN: Should return standard mock tools
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:alice",
            relation="executor",
            resource_type="tool",
        )

        # Assert
        assert len(resources) > 0
        assert all(r.startswith("tool:") for r in resources)
        assert "tool:agent_chat" in resources

    def test_get_mock_conversations_scoped_to_user(self):
        """
        GIVEN: MockResourceGenerator
        WHEN: Requesting conversation resources for specific user
        THEN: Should return user-scoped conversations
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:alice",
            relation="viewer",
            resource_type="conversation",
        )

        # Assert
        assert len(resources) > 0
        assert all(r.startswith("conversation:") for r in resources)
        # All conversations should be scoped to alice
        assert all("alice" in r for r in resources)

    def test_get_mock_conversations_different_user(self):
        """
        GIVEN: MockResourceGenerator
        WHEN: Requesting conversation resources for different users
        THEN: Should return different user-scoped conversations
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        alice_resources = generator.get_resources(
            user_id="user:alice",
            relation="viewer",
            resource_type="conversation",
        )
        bob_resources = generator.get_resources(
            user_id="user:bob",
            relation="viewer",
            resource_type="conversation",
        )

        # Assert - different users get different conversations
        assert alice_resources != bob_resources
        assert all("alice" in r for r in alice_resources)
        assert all("bob" in r for r in bob_resources)

    def test_get_mock_users(self):
        """
        GIVEN: MockResourceGenerator
        WHEN: Requesting user resources
        THEN: Should return mock users
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:admin",
            relation="admin",
            resource_type="user",
        )

        # Assert
        assert len(resources) > 0
        assert all(r.startswith("user:") for r in resources)

    def test_get_unknown_resource_type_returns_empty(self):
        """
        GIVEN: MockResourceGenerator
        WHEN: Requesting unknown resource type
        THEN: Should return empty list
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:alice",
            relation="viewer",
            resource_type="unknown_type",
        )

        # Assert
        assert resources == []

    def test_handles_user_id_with_prefix(self):
        """
        GIVEN: User ID in "user:username" format
        WHEN: Requesting resources
        THEN: Should correctly extract username for scoping
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:charlie",
            relation="viewer",
            resource_type="conversation",
        )

        # Assert
        assert len(resources) > 0
        assert all("charlie" in r for r in resources)

    def test_handles_user_id_without_prefix(self):
        """
        GIVEN: User ID without prefix (just username)
        WHEN: Requesting resources
        THEN: Should correctly use username for scoping
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="david",  # No "user:" prefix
            relation="viewer",
            resource_type="conversation",
        )

        # Assert
        assert len(resources) > 0
        assert all("david" in r for r in resources)


@pytest.mark.xdist_group(name="test_mock_resources")
class TestMockResourceGeneratorConfiguration:
    """Test MockResourceGenerator configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_mock_tools_list(self):
        """
        GIVEN: Default MockResourceGenerator
        WHEN: Getting tool resources
        THEN: Should include standard development tools
        """
        # Arrange
        generator = MockResourceGenerator()

        # Act
        resources = generator.get_resources(
            user_id="user:alice",
            relation="executor",
            resource_type="tool",
        )

        # Assert - should include core tools for development
        expected_tools = [
            "tool:agent_chat",
            "tool:conversation_get",
            "tool:conversation_search",
        ]
        for tool in expected_tools:
            assert tool in resources, f"Expected {tool} in mock tools"
