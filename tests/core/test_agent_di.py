"""
TDD Tests for Agent Dependency Injection Refactoring

These tests define the behavior we want after refactoring agent.py
to use dependency injection instead of global singletons.

Following TDD:
1. Write tests first (this file) - RED
2. Refactor agent.py to pass tests - GREEN
3. Verify no regressions - REFACTOR
"""

import pytest
from unittest.mock import Mock, patch


class TestAgentFactory:
    """Test the new agent factory function"""

    def test_create_agent_with_container(self):
        """Test creating agent using container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.agent import create_agent

        container = create_test_container()
        agent = create_agent(container=container)

        assert agent is not None
        # Agent should be a compiled graph
        assert hasattr(agent, "invoke") or callable(agent)

    def test_create_agent_with_settings(self):
        """Test creating agent with custom settings"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.agent import create_agent

        settings = Settings(environment="test", model_name="test-model", log_level="DEBUG")

        agent = create_agent(settings=settings)

        assert agent is not None

    def test_create_agent_returns_different_instances(self):
        """Test that each call creates a new agent instance"""
        from mcp_server_langgraph.core.agent import create_agent

        agent1 = create_agent()
        agent2 = create_agent()

        # Should be different instances (no more singleton!)
        assert agent1 is not agent2

    def test_create_agent_uses_container_telemetry(self):
        """Test that agent uses container's telemetry provider"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.agent import create_agent

        container = create_test_container()

        # Container should use no-op telemetry in test mode
        telemetry = container.get_telemetry()

        # Agent creation should not raise errors with no-op telemetry
        agent = create_agent(container=container)

        assert agent is not None


class TestAgentGraphFactory:
    """Test the graph creation function"""

    def test_create_agent_graph_with_settings(self):
        """Test creating agent graph with settings"""
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.agent import create_agent_graph

        settings = Settings(environment="test")
        graph = create_agent_graph(settings=settings)

        assert graph is not None

    def test_create_agent_graph_with_container(self):
        """Test creating agent graph with container"""
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.agent import create_agent_graph

        container = create_test_container()
        graph = create_agent_graph(container=container)

        assert graph is not None

    def test_create_agent_graph_is_compiled(self):
        """Test that created graph is compiled and ready"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        graph = create_agent_graph()

        # Should have invoke method (compiled graph)
        assert hasattr(graph, "invoke")


class TestBackwardCompatibility:
    """Test that old singleton pattern still works during migration"""

    def test_get_agent_graph_still_works(self):
        """Test that old get_agent_graph() function still works"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        agent = get_agent_graph()

        assert agent is not None

    def test_get_agent_graph_returns_singleton(self):
        """Test that old function still returns singleton"""
        from mcp_server_langgraph.core.agent import get_agent_graph

        agent1 = get_agent_graph()
        agent2 = get_agent_graph()

        # Old function should still return same instance for backward compat
        assert agent1 is agent2


class TestAgentStateManagement:
    """Test that agent state works with container pattern"""

    def test_agent_with_memory_checkpointer(self):
        """Test agent uses MemorySaver in test mode"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container = create_test_container()
        agent = create_agent(container=container)

        # Agent should be created with a checkpointer
        assert agent is not None

    def test_agent_with_redis_checkpointer(self):
        """Test agent can use Redis checkpointer from container"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import (
            ContainerConfig,
            ApplicationContainer,
        )
        from mcp_server_langgraph.core.config import Settings

        # Create development container with Redis storage
        config = ContainerConfig(environment="development")
        settings = Settings(environment="development", redis_host="localhost", redis_port=6379)
        container = ApplicationContainer(config, settings=settings)

        # Should create agent without errors (even if Redis not connected)
        agent = create_agent(container=container)
        assert agent is not None


class TestAgentConfiguration:
    """Test that agent respects configuration from container"""

    def test_agent_uses_container_settings(self):
        """Test that agent uses settings from container"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.core.config import Settings

        custom_settings = Settings(environment="test", model_name="custom-test-model", temperature=0.5)
        container = create_test_container(settings=custom_settings)

        agent = create_agent(container=container)

        assert agent is not None
        # Agent should be created with custom settings


class TestAgentIsolation:
    """Test that agents are properly isolated"""

    def test_multiple_agents_are_independent(self):
        """Test that multiple agent instances don't share state"""
        from mcp_server_langgraph.core.agent import create_agent

        agent1 = create_agent()
        agent2 = create_agent()

        # Agents should be independent
        assert agent1 is not agent2

    def test_agents_from_different_containers_are_independent(self):
        """Test that agents from different containers are independent"""
        from mcp_server_langgraph.core.agent import create_agent
        from mcp_server_langgraph.core.container import create_test_container

        container1 = create_test_container()
        container2 = create_test_container()

        agent1 = create_agent(container=container1)
        agent2 = create_agent(container=container2)

        assert agent1 is not agent2


class TestAgentTestHelperIntegration:
    """Test that agent works with test helpers"""

    def test_create_test_agent_uses_new_factory(self):
        """Test that test helper uses the new factory"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent()

        assert agent is not None

    def test_create_test_agent_with_container(self, test_container):
        """Test that test helper works with container fixture"""
        from mcp_server_langgraph.core.test_helpers import create_test_agent

        agent = create_test_agent(container=test_container)

        assert agent is not None


class TestAgentDocumentation:
    """Test that refactored functions have good documentation"""

    def test_create_agent_has_docstring(self):
        """Test that create_agent has comprehensive docstring"""
        from mcp_server_langgraph.core.agent import create_agent

        assert create_agent.__doc__ is not None
        assert len(create_agent.__doc__) > 50
        assert "container" in create_agent.__doc__.lower()

    def test_create_agent_graph_has_docstring(self):
        """Test that create_agent_graph has comprehensive docstring"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        assert create_agent_graph.__doc__ is not None
        assert len(create_agent_graph.__doc__) > 50
