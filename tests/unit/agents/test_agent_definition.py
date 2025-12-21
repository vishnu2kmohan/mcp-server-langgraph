"""
Tests for Agent Definition (Phase 6.1)

Following TDD: Write tests FIRST, then implementation.

This module tests the simplified AgentDefinition model following
Claude Agent SDK's pattern for declarative agent configuration.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentDefinitionImport:
    """Test AgentDefinition can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_definition_importable(self) -> None:
        """AgentDefinition should be importable."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        assert AgentDefinition is not None

    def test_agent_registry_importable(self) -> None:
        """AgentRegistry should be importable."""
        from mcp_server_langgraph.agents.definition import AgentRegistry

        assert AgentRegistry is not None


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentDefinitionCreation:
    """Test creating AgentDefinition instances."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_simple_agent_definition(self) -> None:
        """Should create simple agent definition."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="code_reviewer",
            description="Reviews code for issues",
            prompt="You are a code reviewer. Analyze the code carefully.",
        )

        assert agent.name == "code_reviewer"
        assert agent.description == "Reviews code for issues"
        assert "code reviewer" in agent.prompt.lower()

    def test_create_agent_with_tools(self) -> None:
        """Should create agent with tool restrictions."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="file_analyzer",
            description="Analyzes files",
            prompt="Analyze the given files",
            tools=["Read", "Grep", "Glob"],
        )

        assert agent.tools == ["Read", "Grep", "Glob"]

    def test_create_agent_with_model(self) -> None:
        """Should create agent with specific model."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="fast_responder",
            description="Quick responses",
            prompt="Respond quickly",
            model="haiku",
        )

        assert agent.model == "haiku"

    def test_create_agent_with_all_options(self) -> None:
        """Should create agent with all configuration options."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="full_agent",
            description="Full featured agent",
            prompt="You are a versatile agent",
            tools=["Read", "Write", "Edit"],
            model="sonnet",
            max_tokens=4096,
            temperature=0.7,
        )

        assert agent.name == "full_agent"
        assert agent.tools == ["Read", "Write", "Edit"]
        assert agent.model == "sonnet"
        assert agent.max_tokens == 4096
        assert agent.temperature == 0.7


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentDefinitionDefaults:
    """Test AgentDefinition default values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_tools_is_empty(self) -> None:
        """Default tools should be empty (all tools allowed)."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="test",
            description="test",
            prompt="test",
        )

        assert agent.tools is None or agent.tools == []

    def test_default_model_is_none(self) -> None:
        """Default model should be None (use system default)."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="test",
            description="test",
            prompt="test",
        )

        assert agent.model is None

    def test_default_temperature_is_none(self) -> None:
        """Default temperature should be None (use system default)."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="test",
            description="test",
            prompt="test",
        )

        assert agent.temperature is None


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentDefinitionConversion:
    """Test AgentDefinition conversion methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_to_dict_returns_dictionary(self) -> None:
        """to_dict should return dictionary representation."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="test_agent",
            description="Test description",
            prompt="Test prompt",
            tools=["Read"],
            model="sonnet",
        )

        result = agent.to_dict()

        assert isinstance(result, dict)
        assert result["name"] == "test_agent"
        assert result["description"] == "Test description"
        assert result["prompt"] == "Test prompt"
        assert result["tools"] == ["Read"]
        assert result["model"] == "sonnet"

    def test_from_dict_creates_agent_definition(self) -> None:
        """from_dict should create AgentDefinition from dictionary."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        config = {
            "name": "from_dict_agent",
            "description": "Created from dict",
            "prompt": "Dict prompt",
            "tools": ["Write", "Edit"],
            "model": "opus",
        }

        agent = AgentDefinition.from_dict(config)

        assert agent.name == "from_dict_agent"
        assert agent.description == "Created from dict"
        assert agent.tools == ["Write", "Edit"]
        assert agent.model == "opus"


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentRegistry:
    """Test AgentRegistry for managing agent definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_agent_definition(self) -> None:
        """Should register an agent definition."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )

        registry = AgentRegistry()
        agent = AgentDefinition(
            name="reviewer",
            description="Code reviewer",
            prompt="Review code",
        )

        registry.register(agent)

        assert "reviewer" in registry.list_agents()

    def test_get_registered_agent(self) -> None:
        """Should retrieve registered agent by name."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )

        registry = AgentRegistry()
        agent = AgentDefinition(
            name="analyzer",
            description="Data analyzer",
            prompt="Analyze data",
        )

        registry.register(agent)
        retrieved = registry.get("analyzer")

        assert retrieved is not None
        assert retrieved.name == "analyzer"
        assert retrieved.description == "Data analyzer"

    def test_get_nonexistent_agent_returns_none(self) -> None:
        """Should return None for non-existent agent."""
        from mcp_server_langgraph.agents.definition import AgentRegistry

        registry = AgentRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_register_multiple_agents(self) -> None:
        """Should register multiple agents."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )

        registry = AgentRegistry()

        registry.register(
            AgentDefinition(name="agent1", description="First", prompt="First prompt")
        )
        registry.register(
            AgentDefinition(name="agent2", description="Second", prompt="Second prompt")
        )
        registry.register(
            AgentDefinition(name="agent3", description="Third", prompt="Third prompt")
        )

        agents = registry.list_agents()

        assert len(agents) == 3
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

    def test_unregister_agent(self) -> None:
        """Should unregister an agent."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )

        registry = AgentRegistry()
        registry.register(
            AgentDefinition(name="temp", description="Temp", prompt="Temp")
        )

        assert "temp" in registry.list_agents()

        registry.unregister("temp")

        assert "temp" not in registry.list_agents()


@pytest.mark.xdist_group(name="agent_definition")
class TestAgentDefinitionFromSubagent:
    """Test creating AgentDefinition from existing Subagent patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_to_subagent_config_returns_config(self) -> None:
        """to_subagent_config should return config for Subagent creation."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="task_executor",
            description="Executes tasks",
            prompt="You are a task executor. Complete the given task.",
            model="sonnet",
        )

        config = agent.to_subagent_config(task_id="task-123")

        assert config["task_id"] == "task-123"
        assert "task executor" in config["instructions"].lower()
        assert config.get("model") == "sonnet"

    def test_to_subagent_config_includes_system_prompt(self) -> None:
        """to_subagent_config should include prompt as system_prompt."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="test",
            description="Test agent",
            prompt="You are a helpful assistant.",
        )

        config = agent.to_subagent_config(task_id="task-456")

        assert "system_prompt" in config
        assert config["system_prompt"] == "You are a helpful assistant."
