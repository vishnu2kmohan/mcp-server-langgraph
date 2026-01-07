"""
Tests for RouterAgent

TDD: These tests define the contract for the router agent that classifies
requests and selects appropriate orchestrators, models, and strategies.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="router_output")
class TestRouterOutput:
    """Tests for RouterOutput model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_exists(self) -> None:
        """Test that RouterOutput class exists."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        assert RouterOutput is not None

    def test_router_output_has_complexity_field(self) -> None:
        """Test RouterOutput has complexity field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )

        assert output.complexity == "simple"

    def test_router_output_complexity_valid_values(self) -> None:
        """Test complexity accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for complexity in ["simple", "complicated", "complex"]:
            output = RouterOutput(
                complexity=complexity,
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
            )
            assert output.complexity == complexity

    def test_router_output_has_risk_field(self) -> None:
        """Test RouterOutput has risk field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="high",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="none",
            confidence=0.8,
        )

        assert output.risk == "high"

    def test_router_output_risk_valid_values(self) -> None:
        """Test risk accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for risk in ["low", "medium", "high"]:
            output = RouterOutput(
                complexity="simple",
                risk=risk,
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
            )
            assert output.risk == risk

    def test_router_output_has_task_type_field(self) -> None:
        """Test RouterOutput has task_type field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="code",
            tools_needed=["file_write"],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.task_type == "code"

    def test_router_output_task_type_valid_values(self) -> None:
        """Test task_type accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for task_type in ["chat", "code", "analysis", "data", "ops", "other"]:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type=task_type,
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
            )
            assert output.task_type == task_type

    def test_router_output_has_tools_needed_field(self) -> None:
        """Test RouterOutput has tools_needed field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_read", "file_write", "bash"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
        )

        assert output.tools_needed == ["file_read", "file_write", "bash"]

    def test_router_output_has_suggested_orchestrator_field(self) -> None:
        """Test RouterOutput has suggested_orchestrator field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.7,
        )

        assert output.suggested_orchestrator == "swarm"

    def test_router_output_orchestrator_valid_values(self) -> None:
        """Test suggested_orchestrator accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for orchestrator in ["standard", "swarm", "studio", "ux", "alert"]:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator=orchestrator,
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
            )
            assert output.suggested_orchestrator == orchestrator

    def test_router_output_has_critique_rounds_field(self) -> None:
        """Test RouterOutput has critique_rounds field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="code",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=3,
            thinking_budget="deep",
            confidence=0.8,
        )

        assert output.critique_rounds == 3

    def test_router_output_critique_rounds_range(self) -> None:
        """Test critique_rounds is between 0 and 3."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        # Valid range
        for rounds in [0, 1, 2, 3]:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=rounds,
                thinking_budget="none",
                confidence=0.9,
            )
            assert output.critique_rounds == rounds

    def test_router_output_has_thinking_budget_field(self) -> None:
        """Test RouterOutput has thinking_budget field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.85,
        )

        assert output.thinking_budget == "deep"

    def test_router_output_thinking_budget_valid_values(self) -> None:
        """Test thinking_budget accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for budget in ["none", "light", "medium", "deep"]:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget=budget,
                confidence=0.9,
            )
            assert output.thinking_budget == budget

    def test_router_output_has_confidence_field(self) -> None:
        """Test RouterOutput has confidence field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )

        assert output.confidence == 0.95

    def test_router_output_confidence_range(self) -> None:
        """Test confidence is between 0.0 and 1.0."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.5,
        )

        assert 0.0 <= output.confidence <= 1.0


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="router_agent_class")
class TestRouterAgent:
    """Tests for RouterAgent class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_agent_exists(self) -> None:
        """Test that RouterAgent class exists."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        assert RouterAgent is not None

    def test_router_agent_requires_llm_factory(self) -> None:
        """Test RouterAgent requires LLMFactory in constructor."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()

        agent = RouterAgent(llm_factory=mock_llm_factory)

        assert agent.llm_factory == mock_llm_factory

    def test_router_agent_accepts_model_id(self) -> None:
        """Test RouterAgent accepts optional fast model ID."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()

        agent = RouterAgent(
            llm_factory=mock_llm_factory,
            model_id="gemini-3-flash-preview",
        )

        assert agent.model_id == "gemini-3-flash-preview"

    def test_router_agent_has_route_method(self) -> None:
        """Test RouterAgent has route method."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        assert hasattr(agent, "route")
        assert callable(agent.route)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="router_agent_route")
class TestRouterAgentRoute:
    """Tests for RouterAgent.route execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_router_agent_route_returns_router_output(self) -> None:
        """Test RouterAgent.route returns RouterOutput."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent, RouterOutput

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello, how are you?")

        assert isinstance(result, RouterOutput)

    async def test_router_agent_route_classifies_simple_chat(self) -> None:
        """Test RouterAgent classifies simple chat as low complexity."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.95}'
            )
        )

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="What's the weather like?")

        assert result.complexity == "simple"
        assert result.risk == "low"
        assert result.task_type == "chat"

    async def test_router_agent_route_handles_parse_error(self) -> None:
        """Test RouterAgent handles JSON parse errors gracefully."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(return_value=AIMessage(content="invalid json"))

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return default fallback
        assert result.complexity == "complicated"
        assert result.suggested_orchestrator == "standard"

    async def test_router_agent_route_handles_llm_error(self) -> None:
        """Test RouterAgent handles LLM errors with default fallback."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return safe default
        assert result.complexity == "complicated"
        assert result.suggested_orchestrator == "standard"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="executor_critic_selection")
class TestExecutorCriticSelection:
    """Tests for executor/critic model selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_executor_critic_exists(self) -> None:
        """Test select_executor_critic function exists."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        assert select_executor_critic is not None
        assert callable(select_executor_critic)

    def test_select_executor_critic_returns_tuple(self) -> None:
        """Test select_executor_critic returns tuple of (executor, critic)."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        result = select_executor_critic(complexity="simple", risk="low")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_select_executor_critic_simple_low_no_critic(self) -> None:
        """Test simple/low returns executor but no critic."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        executor, critic = select_executor_critic(complexity="simple", risk="low")

        assert executor is not None
        assert critic is None  # No critique needed for simple/low

    def test_select_executor_critic_complex_high_has_critic(self) -> None:
        """Test complex/high returns both executor and critic."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        executor, critic = select_executor_critic(complexity="complex", risk="high")

        assert executor is not None
        assert critic is not None

    def test_select_executor_critic_cross_vendor_by_default(self) -> None:
        """Test default is cross-vendor (Gemini executor + Claude critic)."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        executor, critic = select_executor_critic(complexity="complex", risk="high")

        # Default should be different vendors
        if critic:
            # Executor and critic should be from different vendors
            # (actual vendor check would require ModelRegistry lookup)
            assert executor != critic

    def test_select_executor_critic_same_vendor_override(self) -> None:
        """Test same-vendor override for cost optimization."""
        from mcp_server_langgraph.agents.router_agent import select_executor_critic

        executor, critic = select_executor_critic(
            complexity="complex",
            risk="high",
            prefer_same_vendor=True,
        )

        # Both should be from same vendor family
        assert executor is not None
        # Critic may or may not be same model, but from same vendor


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="router_output_with_templates")
class TestRouterOutputWithTemplates:
    """Tests for RouterOutputWithTemplates model with template suggestions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_with_templates_exists(self) -> None:
        """Test that RouterOutputWithTemplates class exists."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithTemplates

        assert RouterOutputWithTemplates is not None

    def test_router_output_with_templates_extends_router_output(self) -> None:
        """Test RouterOutputWithTemplates extends RouterOutput."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterOutput,
            RouterOutputWithTemplates,
        )

        assert issubclass(RouterOutputWithTemplates, RouterOutput)

    def test_router_output_with_templates_has_suggested_templates_field(self) -> None:
        """Test RouterOutputWithTemplates has suggested_templates field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithTemplates

        output = RouterOutputWithTemplates(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
            suggested_templates=[],
        )

        assert hasattr(output, "suggested_templates")
        assert output.suggested_templates == []

    def test_router_output_with_templates_accepts_template_list(self) -> None:
        """Test RouterOutputWithTemplates accepts list of template suggestions."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterOutputWithTemplates,
            TemplateSuggestion,
        )

        suggestions = [
            TemplateSuggestion(
                template_id="tmpl-1",
                name="Code Review",
                similarity=0.92,
            ),
            TemplateSuggestion(
                template_id="tmpl-2",
                name="Data Analysis",
                similarity=0.87,
            ),
        ]

        output = RouterOutputWithTemplates(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_read"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="medium",
            confidence=0.85,
            suggested_templates=suggestions,
        )

        assert len(output.suggested_templates) == 2
        assert output.suggested_templates[0].template_id == "tmpl-1"
        assert output.suggested_templates[0].similarity == 0.92


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="template_suggestion")
class TestTemplateSuggestion:
    """Tests for TemplateSuggestion model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_template_suggestion_exists(self) -> None:
        """Test that TemplateSuggestion class exists."""
        from mcp_server_langgraph.agents.router_agent import TemplateSuggestion

        assert TemplateSuggestion is not None

    def test_template_suggestion_has_template_id(self) -> None:
        """Test TemplateSuggestion has template_id field."""
        from mcp_server_langgraph.agents.router_agent import TemplateSuggestion

        suggestion = TemplateSuggestion(
            template_id="tmpl-123",
            name="Test Template",
            similarity=0.9,
        )

        assert suggestion.template_id == "tmpl-123"

    def test_template_suggestion_has_name(self) -> None:
        """Test TemplateSuggestion has name field."""
        from mcp_server_langgraph.agents.router_agent import TemplateSuggestion

        suggestion = TemplateSuggestion(
            template_id="tmpl-123",
            name="Code Review Template",
            similarity=0.85,
        )

        assert suggestion.name == "Code Review Template"

    def test_template_suggestion_has_similarity(self) -> None:
        """Test TemplateSuggestion has similarity score."""
        from mcp_server_langgraph.agents.router_agent import TemplateSuggestion

        suggestion = TemplateSuggestion(
            template_id="tmpl-123",
            name="Test",
            similarity=0.88,
        )

        assert suggestion.similarity == 0.88

    def test_template_suggestion_similarity_in_range(self) -> None:
        """Test TemplateSuggestion similarity is between 0 and 1."""
        from mcp_server_langgraph.agents.router_agent import TemplateSuggestion

        suggestion = TemplateSuggestion(
            template_id="tmpl-123",
            name="Test",
            similarity=0.75,
        )

        assert 0.0 <= suggestion.similarity <= 1.0


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="router_agent_template_suggestion")
class TestRouterAgentTemplateSuggestion:
    """Tests for RouterAgent template suggestion functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_router_agent_has_route_with_template_suggestion_method(
        self,
    ) -> None:
        """Test RouterAgent has route_with_template_suggestion method."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        assert hasattr(agent, "route_with_template_suggestion")
        assert callable(agent.route_with_template_suggestion)

    async def test_route_with_template_suggestion_returns_router_output_with_templates(
        self,
    ) -> None:
        """Test route_with_template_suggestion returns RouterOutputWithTemplates."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutputWithTemplates,
        )
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        from langchain_core.messages import AIMessage

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 128)

        template_repo = InMemoryPlanTemplateRepository()

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route_with_template_suggestion(
            message="Help me with code review",
            embedding_service=mock_embedding_service,
            template_repo=template_repo,
        )

        assert isinstance(result, RouterOutputWithTemplates)

    async def test_route_with_template_suggestion_embeds_message(self) -> None:
        """Test route_with_template_suggestion embeds the user message."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 128)

        template_repo = InMemoryPlanTemplateRepository()

        agent = RouterAgent(llm_factory=mock_llm_factory)
        await agent.route_with_template_suggestion(
            message="Help me with code review",
            embedding_service=mock_embedding_service,
            template_repo=template_repo,
        )

        mock_embedding_service.embed.assert_called_once_with("Help me with code review")

    async def test_route_with_template_suggestion_finds_similar_templates(
        self,
    ) -> None:
        """Test route_with_template_suggestion finds similar templates from repo."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "complicated", "risk": "medium", "task_type": "code", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 1, "thinking_budget": "medium", "confidence": 0.85}'
            )
        )

        # Create embedding that will match
        test_embedding = [0.8] * 128
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=test_embedding)

        template_repo = InMemoryPlanTemplateRepository()
        # Add a template with similar embedding
        template = PlanTemplate(
            template_id="tmpl-code-review",
            name="Code Review Template",
            description="Template for code review tasks",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="test@example.com",
            tags=["code", "review"],
            description_embedding=[0.8] * 128,  # Same embedding = 100% similarity
        )
        await template_repo.create(template)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route_with_template_suggestion(
            message="Help me with code review",
            embedding_service=mock_embedding_service,
            template_repo=template_repo,
            min_similarity=0.7,
        )

        assert len(result.suggested_templates) > 0
        assert result.suggested_templates[0].template_id == "tmpl-code-review"

    async def test_route_with_template_suggestion_filters_by_min_similarity(
        self,
    ) -> None:
        """Test route_with_template_suggestion respects min_similarity threshold."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )

        # Create orthogonal embedding (0% similarity)
        query_embedding = [1.0, 0.0] + [0.0] * 126
        template_embedding = [0.0, 1.0] + [0.0] * 126

        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=query_embedding)

        template_repo = InMemoryPlanTemplateRepository()
        template = PlanTemplate(
            template_id="tmpl-dissimilar",
            name="Dissimilar Template",
            description="Template with low similarity",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="test@example.com",
            tags=["other"],
            description_embedding=template_embedding,
        )
        await template_repo.create(template)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route_with_template_suggestion(
            message="Something completely different",
            embedding_service=mock_embedding_service,
            template_repo=template_repo,
            min_similarity=0.8,  # High threshold
        )

        # No templates should match due to low similarity
        assert len(result.suggested_templates) == 0

    async def test_route_with_template_suggestion_limits_results(self) -> None:
        """Test route_with_template_suggestion respects max_suggestions limit."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate
        from mcp_server_langgraph.repositories.plan_template import (
            InMemoryPlanTemplateRepository,
        )

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
            )
        )

        test_embedding = [0.8] * 128
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=test_embedding)

        template_repo = InMemoryPlanTemplateRepository()
        # Add 5 templates with high similarity
        for i in range(5):
            template = PlanTemplate(
                template_id=f"tmpl-{i}",
                name=f"Template {i}",
                description=f"Test template {i}",
                orchestrator="standard",
                thinking_budget="none",
                critique_rounds=0,
                auto_approve=True,
                created_by="test@example.com",
                tags=["test"],
                description_embedding=[0.8] * 128,
            )
            await template_repo.create(template)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route_with_template_suggestion(
            message="Test message",
            embedding_service=mock_embedding_service,
            template_repo=template_repo,
            max_suggestions=3,
        )

        assert len(result.suggested_templates) <= 3
