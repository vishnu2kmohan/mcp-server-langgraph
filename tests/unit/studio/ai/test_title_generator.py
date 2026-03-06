"""
Title Generator Unit Tests

Tests for AI-powered session title generation.
TDD: Tests written FIRST (RED phase).

The title generator should:
1. Generate concise, descriptive titles from user messages
2. Use LLM when available, fallback to heuristics
3. Respect max title length
4. Use LLMFactory for resilient LLM calls (SOLID compliance)
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit]


class TestSessionTitleGenerator:
    """Tests for SessionTitleGenerator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_returns_title_for_message(self) -> None:
        """
        GIVEN a user message
        WHEN generate is called
        THEN should return a descriptive title
        """
        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        generator = SessionTitleGenerator(enable_llm=False)
        title = await generator.generate("Help me write a Python function to sort a list")

        assert title is not None
        assert len(title) > 0
        assert len(title) <= 50

    @pytest.mark.asyncio
    async def test_generate_returns_default_for_empty_message(self) -> None:
        """
        GIVEN an empty message
        WHEN generate is called
        THEN should return "New Chat"
        """
        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        generator = SessionTitleGenerator(enable_llm=False)
        title = await generator.generate("")

        assert title == "New Chat"

    @pytest.mark.asyncio
    async def test_generate_respects_max_length(self) -> None:
        """
        GIVEN a message that would generate a long title
        WHEN generate is called
        THEN title should be truncated to max length
        """
        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        generator = SessionTitleGenerator(enable_llm=False, max_title_length=30)
        title = await generator.generate("I need help with implementing a very complex authentication system")

        assert len(title) <= 30

    @pytest.mark.asyncio
    async def test_generate_extracts_key_phrases(self) -> None:
        """
        GIVEN a message with common prefixes
        WHEN generate is called with heuristics
        THEN should extract key phrases
        """
        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        generator = SessionTitleGenerator(enable_llm=False)
        title = await generator.generate("Can you help me debug this API error?")

        assert title is not None
        assert len(title) > 0
        # Should not contain the prefix "Can you help me"
        assert not title.lower().startswith("can you")


class TestSessionTitleGeneratorLLMFactory:
    """Tests for LLMFactory integration (SOLID compliance).

    These tests verify that SessionTitleGenerator uses LLMFactory
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
        WHEN SessionTitleGenerator is initialized with llm_factory parameter
        THEN it should use the injected factory for LLM calls
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        # Create mock LLM factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Python Sorting Help"))

        generator = SessionTitleGenerator(enable_llm=True, llm_factory=mock_factory)
        title = await generator.generate("Help me write a Python function to sort a list")

        # Factory's ainvoke should have been called
        mock_factory.ainvoke.assert_called_once()
        assert "Python" in title or "Sorting" in title

    @pytest.mark.asyncio
    async def test_lazy_initializes_llm_factory_when_not_provided(self) -> None:
        """
        GIVEN no LLM factory provided
        WHEN generate is called with LLM enabled
        THEN it should lazy-initialize the factory from settings
        """
        from unittest.mock import patch

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        # Create a mock factory
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Lazy Init Title"))

        # Patch at the source module
        with patch(
            "mcp_server_langgraph.llm.factory.create_llm_from_config",
            return_value=mock_factory,
        ) as mock_create:
            generator = SessionTitleGenerator(enable_llm=True)
            title = await generator.generate("Some message that needs a title")

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
        from mcp_server_langgraph.studio.ai.title_generator import (
            SessionTitleGenerator,
        )

        # Create mock LLM factory that fails
        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        generator = SessionTitleGenerator(enable_llm=True, llm_factory=mock_factory)
        title = await generator.generate("Debug the authentication error")

        # Should fall back to heuristics and return a title
        assert title is not None
        assert len(title) > 0
