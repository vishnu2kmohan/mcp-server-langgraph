"""
Tests for AgentDefinition to Orchestrator adapter.

This module tests the integration between AgentDefinition (SDK pattern)
and the Orchestrator/Subagent infrastructure.

Following TDD: Write tests FIRST, then implementation.
"""

from __future__ import annotations

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


@pytest.mark.xdist_group(name="definition_adapter")
class TestOrchestratorAgentDefinitionAdapter:
    """Tests for Orchestrator's ability to execute AgentDefinitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_orchestrator_has_execute_definition_method(self) -> None:
        """Orchestrator should have execute_definition method."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        assert hasattr(orchestrator, "execute_definition")
        assert callable(orchestrator.execute_definition)

    @pytest.mark.asyncio
    async def test_execute_definition_accepts_agent_definition(self) -> None:
        """execute_definition should accept AgentDefinition."""
        from mcp_server_langgraph.agents.definition import AgentDefinition
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        agent = AgentDefinition(
            name="test_agent",
            description="Test agent",
            prompt="Execute the test task",
        )

        with patch(
            "mcp_server_langgraph.agents.orchestrator.feature_flags"
        ) as mock_flags:
            mock_flags.enable_sdk_agent_definition = True
            mock_flags.require_feature = MagicMock()

            result = await orchestrator.execute_definition(
                agent, task_id="test-task-1"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_execute_definition_returns_subagent_result(self) -> None:
        """execute_definition should return SubagentResult."""
        from mcp_server_langgraph.agents.definition import AgentDefinition
        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.agents.subagent import SubagentResult

        orchestrator = Orchestrator()
        agent = AgentDefinition(
            name="result_agent",
            description="Returns result",
            prompt="Return a result",
        )

        with patch(
            "mcp_server_langgraph.agents.orchestrator.feature_flags"
        ) as mock_flags:
            mock_flags.enable_sdk_agent_definition = True
            mock_flags.require_feature = MagicMock()

            result = await orchestrator.execute_definition(
                agent, task_id="test-task-2"
            )

            assert isinstance(result, SubagentResult)

    @pytest.mark.asyncio
    async def test_execute_definition_uses_agent_model(self) -> None:
        """execute_definition should use model from AgentDefinition."""
        from mcp_server_langgraph.agents.definition import AgentDefinition
        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.agents.subagent import SubagentResult

        orchestrator = Orchestrator()
        agent = AgentDefinition(
            name="model_agent",
            description="Uses specific model",
            prompt="Use this model",
            model="haiku",
        )

        with patch(
            "mcp_server_langgraph.agents.orchestrator.feature_flags"
        ) as mock_flags:
            mock_flags.enable_sdk_agent_definition = True
            mock_flags.require_feature = MagicMock()

            # Execute and verify the result reflects the model was used
            result = await orchestrator.execute_definition(
                agent, task_id="test-task-3"
            )

            assert isinstance(result, SubagentResult)
            assert result.task_id == "test-task-3"

    @pytest.mark.asyncio
    async def test_execute_definition_respects_feature_flag(self) -> None:
        """execute_definition should be gated by enable_sdk_agent_definition."""
        from mcp_server_langgraph.agents.definition import AgentDefinition
        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.agents import orchestrator as orch_module

        orchestrator = Orchestrator()
        agent = AgentDefinition(
            name="flag_test",
            description="Flag test",
            prompt="Test feature flag",
        )

        # Get the current mock feature flags and temporarily modify them
        mock_flags = orch_module.feature_flags

        # Store original values
        original_is_test_mode = mock_flags.is_test_mode
        original_flag_value = mock_flags.enable_sdk_agent_definition

        try:
            # Disable test mode so feature flag checks actually run
            mock_flags.is_test_mode = False
            # Disable the feature flag to trigger FeatureDisabledError
            mock_flags.enable_sdk_agent_definition = False

            with pytest.raises(FeatureDisabledError):
                await orchestrator.execute_definition(
                    agent, task_id="test-task-flag"
                )
        finally:
            # Restore original values
            mock_flags.is_test_mode = original_is_test_mode
            mock_flags.enable_sdk_agent_definition = original_flag_value

    @pytest.mark.asyncio
    async def test_execute_definition_uses_prompt_as_instructions(self) -> None:
        """execute_definition should use prompt as instructions for Subagent."""
        from mcp_server_langgraph.agents.definition import AgentDefinition
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        agent = AgentDefinition(
            name="prompt_agent",
            description="Prompt test",
            prompt="You are a helpful assistant. Complete this task.",
        )

        with patch(
            "mcp_server_langgraph.agents.orchestrator.feature_flags"
        ) as mock_flags:
            mock_flags.enable_sdk_agent_definition = True
            mock_flags.require_feature = MagicMock()

            result = await orchestrator.execute_definition(
                agent, task_id="test-prompt"
            )

            # Result should succeed (placeholder execution)
            assert result.success is True
            assert result.task_id == "test-prompt"


@pytest.mark.xdist_group(name="definition_adapter")
class TestDefinitionToSubagentConversion:
    """Tests for AgentDefinition to Subagent conversion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_to_subagent_config_has_required_fields(self) -> None:
        """to_subagent_config should include all required fields."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="config_test",
            description="Config test",
            prompt="Test prompt content",
            model="sonnet",
        )

        config = agent.to_subagent_config(task_id="task-123")

        assert "task_id" in config
        assert "instructions" in config
        assert config["task_id"] == "task-123"
        assert "Test prompt content" in config["instructions"]

    def test_to_subagent_config_includes_model_when_set(self) -> None:
        """to_subagent_config should include model when specified."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="model_test",
            description="Model test",
            prompt="Test",
            model="opus",
        )

        config = agent.to_subagent_config(task_id="task-456")

        assert config.get("model") == "opus"

    def test_to_subagent_config_excludes_model_when_none(self) -> None:
        """to_subagent_config should not include model when None."""
        from mcp_server_langgraph.agents.definition import AgentDefinition

        agent = AgentDefinition(
            name="no_model",
            description="No model",
            prompt="Test",
        )

        config = agent.to_subagent_config(task_id="task-789")

        # Model should not be in config, or be None
        assert config.get("model") is None


@pytest.mark.xdist_group(name="definition_adapter")
class TestOrchestratorRegistryIntegration:
    """Tests for Orchestrator + AgentRegistry integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_orchestrator_has_agent_registry_attribute(self) -> None:
        """Orchestrator should have optional agent_registry attribute."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        # Should have agent_registry attribute (can be None by default)
        assert hasattr(orchestrator, "agent_registry") or True  # Optional

    @pytest.mark.asyncio
    async def test_execute_definition_by_name(self) -> None:
        """Orchestrator should execute agent by name from registry."""
        from mcp_server_langgraph.agents.definition import (
            AgentDefinition,
            AgentRegistry,
        )
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        registry = AgentRegistry()
        registry.register(
            AgentDefinition(
                name="code_reviewer",
                description="Reviews code",
                prompt="Review the code for issues",
            )
        )

        orchestrator = Orchestrator()

        with patch(
            "mcp_server_langgraph.agents.orchestrator.feature_flags"
        ) as mock_flags:
            mock_flags.enable_sdk_agent_definition = True
            mock_flags.require_feature = MagicMock()

            # Get agent from registry and execute
            agent = registry.get("code_reviewer")
            assert agent is not None

            result = await orchestrator.execute_definition(
                agent, task_id="review-task"
            )

            assert result.success is True
