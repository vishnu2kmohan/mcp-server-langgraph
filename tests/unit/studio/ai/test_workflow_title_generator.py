"""
Workflow Title Generator Unit Tests

Tests for AI-powered workflow title generation.
TDD: Tests written FIRST (RED phase).

The workflow title generator should:
1. Generate concise, descriptive titles from description and/or session context
2. Use LLM when available, fallback to heuristics
3. Respect max title length
4. Use LLMFactory for resilient LLM calls (SOLID compliance)
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="test_workflow_title_generator")
class TestWorkflowTitleGenerator:
    """Tests for WorkflowTitleGenerator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_returns_title_for_description(self) -> None:
        """
        GIVEN a workflow description
        WHEN generate is called
        THEN should return a descriptive title
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate(description="Automated customer onboarding with email verification")

        assert title is not None
        assert len(title) > 0
        assert len(title) <= 60

    @pytest.mark.asyncio
    async def test_generate_returns_title_for_session_context(self) -> None:
        """
        GIVEN session context only
        WHEN generate is called
        THEN should return a descriptive title
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate(session_context="Help me create a workflow for new customer signup")

        assert title is not None
        assert len(title) > 0
        assert len(title) <= 60

    @pytest.mark.asyncio
    async def test_generate_returns_default_for_no_context(self) -> None:
        """
        GIVEN no description or session context
        WHEN generate is called
        THEN should return "New Workflow"
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate()

        assert title == "New Workflow"

    @pytest.mark.asyncio
    async def test_generate_returns_default_for_empty_strings(self) -> None:
        """
        GIVEN empty strings for description and session context
        WHEN generate is called
        THEN should return "New Workflow"
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate(description="", session_context="")

        assert title == "New Workflow"

    @pytest.mark.asyncio
    async def test_generate_respects_max_length(self) -> None:
        """
        GIVEN a description that would generate a long title
        WHEN generate is called
        THEN title should be truncated to max length
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False, max_title_length=30)
        title = await generator.generate(
            description="I need help with implementing a very complex authentication system with multi-factor authentication"
        )

        assert len(title) <= 30

    @pytest.mark.asyncio
    async def test_generate_removes_common_prefixes(self) -> None:
        """
        GIVEN a session context with common prefixes
        WHEN generate is called with heuristics
        THEN should remove common prefixes
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate(session_context="Help me create a workflow for data processing")

        assert title is not None
        assert len(title) > 0
        # Should not contain common prefixes
        assert not title.lower().startswith("help me")

    @pytest.mark.asyncio
    async def test_generate_uses_both_description_and_context(self) -> None:
        """
        GIVEN both description and session context
        WHEN generate is called
        THEN should combine context for title generation
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        generator = WorkflowTitleGenerator(enable_llm=False)
        title = await generator.generate(
            description="Email automation pipeline", session_context="Automate customer welcome emails"
        )

        assert title is not None
        assert len(title) > 0


@pytest.mark.xdist_group(name="test_workflow_title_generator_llm")
class TestWorkflowTitleGeneratorLLMFactory:
    """Tests for LLMFactory integration (SOLID compliance).

    These tests verify that WorkflowTitleGenerator uses LLMFactory
    for resilient LLM calls with circuit breaker, retry, timeout,
    and bulkhead patterns.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_accepts_llm_factory_via_dependency_injection(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN WorkflowTitleGenerator is initialized with llm_factory parameter
        THEN it should use the injected factory for LLM calls
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        # Create mock LLM factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Customer Onboarding Pipeline"))

        generator = WorkflowTitleGenerator(enable_llm=True, llm_factory=mock_factory)
        title = await generator.generate(description="Automated customer onboarding with email verification")

        # Factory's ainvoke should have been called
        mock_factory.ainvoke.assert_called_once()
        assert "Customer" in title or "Onboarding" in title or "Pipeline" in title

    @pytest.mark.asyncio
    async def test_lazy_initializes_llm_factory_when_not_provided(self) -> None:
        """
        GIVEN no LLM factory provided
        WHEN generate is called with LLM enabled
        THEN it should lazy-initialize the factory from settings
        """
        from unittest.mock import patch

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        # Create a mock factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Lazy Init Workflow Title"))

        # Patch at the source module
        with patch(
            "mcp_server_langgraph.llm.factory.create_llm_from_config",
            return_value=mock_factory,
        ) as mock_create:
            generator = WorkflowTitleGenerator(enable_llm=True)
            title = await generator.generate(description="Some workflow that needs a title")

            # Should have lazily created the factory
            mock_create.assert_called_once()
            assert title is not None

    @pytest.mark.asyncio
    async def test_falls_back_to_heuristics_on_llm_error(self) -> None:
        """
        GIVEN an LLMFactory that raises an error
        WHEN generate is called
        THEN it should fall back to heuristic title generation
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            WorkflowTitleGenerator,
        )

        # Create mock LLM factory that fails
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        generator = WorkflowTitleGenerator(enable_llm=True, llm_factory=mock_factory)
        title = await generator.generate(description="Data processing pipeline for analytics")

        # Should fall back to heuristics and return a title
        assert title is not None
        assert len(title) > 0


@pytest.mark.xdist_group(name="test_workflow_title_generator_convenience")
class TestWorkflowTitleGeneratorConvenience:
    """Tests for convenience function and singleton pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_workflow_title_convenience_function(self) -> None:
        """
        GIVEN description and session context
        WHEN generate_workflow_title convenience function is called
        THEN it should return a title using the singleton generator
        """
        from unittest.mock import patch

        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            generate_workflow_title,
        )

        # Patch the singleton to use a test generator
        with patch(
            "mcp_server_langgraph.studio.ai.workflow_title_generator._workflow_title_generator",
            None,
        ):
            title = await generate_workflow_title(description="Test workflow description")

            assert title is not None
            assert len(title) > 0

    @pytest.mark.asyncio
    async def test_get_workflow_title_generator_returns_singleton(self) -> None:
        """
        GIVEN the module is loaded
        WHEN get_workflow_title_generator is called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.studio.ai.workflow_title_generator import (
            get_workflow_title_generator,
        )

        generator1 = get_workflow_title_generator()
        generator2 = get_workflow_title_generator()

        # Should be the same instance (singleton)
        assert generator1 is generator2
