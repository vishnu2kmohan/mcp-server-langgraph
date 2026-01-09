"""Unit tests for semantic skill search in SkillsToolHandler.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify that:
1. When enable_semantic_skill_search=True and SkillSearchTool is available,
   semantic vector search is used
2. When feature flag is disabled, falls back to string-based search
3. When SkillSearchTool is unavailable, falls back to string-based search

ADR Reference: ADR-0092, ADR-0099
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler
from mcp_server_langgraph.skills import Skill, SkillDiscovery, SkillRegistry
from mcp_server_langgraph.skills.search import SkillSearchResult, SkillSearchTool

pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.mcp]


@pytest.fixture
def mock_auth():
    """Create a mock auth middleware."""
    return MagicMock()


@pytest.fixture
def mock_agent_graph():
    """Create a mock agent graph."""
    return MagicMock()


@pytest.fixture
def mock_skill_registry():
    """Create a mock skill registry with test skills."""
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="web-research",
            description="Search the web for information using DuckDuckGo",
            instructions="Use this skill to search the web",
            version="1.0.0",
            tags=["research", "web", "search"],
        )
    )
    registry.register(
        Skill(
            name="code-review",
            description="Review code for quality and best practices",
            instructions="Use this skill to review code",
            version="1.0.0",
            tags=["code", "review", "quality"],
        )
    )
    return registry


@pytest.fixture
def mock_skill_search_tool():
    """Create a mock SkillSearchTool for semantic search."""
    mock_tool = AsyncMock(spec=SkillSearchTool)
    mock_tool.search = AsyncMock(
        return_value=[
            SkillSearchResult(
                skill_id="web-research",
                name="web-research",
                description="Search the web for information using DuckDuckGo",
                score=0.95,
                tags=["research", "web", "search"],
            )
        ]
    )
    return mock_tool


@pytest.mark.xdist_group(name="test_skills_handler")
class TestSkillsSemanticSearch:
    """Test semantic skill search integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_used_when_enabled(
        self,
        mock_auth,
        mock_agent_graph,
        mock_skill_registry,
        mock_skill_search_tool,
    ):
        """
        GIVEN: enable_semantic_skill_search=True and SkillSearchTool is configured
        WHEN: Calling handle_search_skills
        THEN: Should use SkillSearchTool for semantic vector search
        """
        handler = SkillsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            skill_registry=mock_skill_registry,
            skill_search_tool=mock_skill_search_tool,
        )

        with patch(
            "mcp_server_langgraph.mcp.handlers.skills.feature_flags"
        ) as mock_flags:
            mock_flags.enable_semantic_skill_search = True

            result = await handler.handle_search_skills(
                arguments={"query": "find web search tool"},
                span=MagicMock(),
                user_id="user:alice",
            )

        # Verify semantic search was called
        mock_skill_search_tool.search.assert_called_once_with(
            "find web search tool",
            limit=10,
            min_score=0.0,
        )

        # Verify result contains semantic search output
        assert len(result) == 1
        assert "web-research" in result[0].text

    @pytest.mark.asyncio
    async def test_fallback_to_string_search_when_flag_disabled(
        self,
        mock_auth,
        mock_agent_graph,
        mock_skill_registry,
        mock_skill_search_tool,
    ):
        """
        GIVEN: enable_semantic_skill_search=False
        WHEN: Calling handle_search_skills
        THEN: Should fall back to SkillDiscovery.search (string matching)
        """
        handler = SkillsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            skill_registry=mock_skill_registry,
            skill_search_tool=mock_skill_search_tool,
        )

        with patch(
            "mcp_server_langgraph.mcp.handlers.skills.feature_flags"
        ) as mock_flags:
            mock_flags.enable_semantic_skill_search = False

            result = await handler.handle_search_skills(
                arguments={"query": "web"},
                span=MagicMock(),
                user_id="user:alice",
            )

        # Verify semantic search was NOT called
        mock_skill_search_tool.search.assert_not_called()

        # Verify result still works (from string search)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fallback_to_string_search_when_tool_not_available(
        self,
        mock_auth,
        mock_agent_graph,
        mock_skill_registry,
    ):
        """
        GIVEN: enable_semantic_skill_search=True but SkillSearchTool is None
        WHEN: Calling handle_search_skills
        THEN: Should fall back to SkillDiscovery.search (string matching)
        """
        handler = SkillsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            skill_registry=mock_skill_registry,
            skill_search_tool=None,  # No semantic search available
        )

        with patch(
            "mcp_server_langgraph.mcp.handlers.skills.feature_flags"
        ) as mock_flags:
            mock_flags.enable_semantic_skill_search = True

            result = await handler.handle_search_skills(
                arguments={"query": "web"},
                span=MagicMock(),
                user_id="user:alice",
            )

        # Verify result works with fallback
        assert len(result) == 1
        assert "web-research" in result[0].text

    @pytest.mark.asyncio
    async def test_semantic_search_respects_limit_and_min_score(
        self,
        mock_auth,
        mock_agent_graph,
        mock_skill_registry,
        mock_skill_search_tool,
    ):
        """
        GIVEN: enable_semantic_skill_search=True with limit/min_score args
        WHEN: Calling handle_search_skills with custom limit and min_score
        THEN: Should pass limit and min_score to SkillSearchTool
        """
        handler = SkillsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            skill_registry=mock_skill_registry,
            skill_search_tool=mock_skill_search_tool,
        )

        with patch(
            "mcp_server_langgraph.mcp.handlers.skills.feature_flags"
        ) as mock_flags:
            mock_flags.enable_semantic_skill_search = True

            await handler.handle_search_skills(
                arguments={
                    "query": "code review",
                    "limit": 5,
                    "min_score": 0.7,
                },
                span=MagicMock(),
                user_id="user:alice",
            )

        mock_skill_search_tool.search.assert_called_once_with(
            "code review",
            limit=5,
            min_score=0.7,
        )

    @pytest.mark.asyncio
    async def test_semantic_search_error_falls_back_to_string_search(
        self,
        mock_auth,
        mock_agent_graph,
        mock_skill_registry,
        mock_skill_search_tool,
    ):
        """
        GIVEN: enable_semantic_skill_search=True but SkillSearchTool raises error
        WHEN: Calling handle_search_skills
        THEN: Should gracefully fall back to SkillDiscovery.search
        """
        mock_skill_search_tool.search = AsyncMock(
            side_effect=Exception("Embedding service unavailable")
        )

        handler = SkillsToolHandler(
            auth=mock_auth,
            agent_graph=mock_agent_graph,
            skill_registry=mock_skill_registry,
            skill_search_tool=mock_skill_search_tool,
        )

        with patch(
            "mcp_server_langgraph.mcp.handlers.skills.feature_flags"
        ) as mock_flags:
            mock_flags.enable_semantic_skill_search = True

            result = await handler.handle_search_skills(
                arguments={"query": "web"},
                span=MagicMock(),
                user_id="user:alice",
            )

        # Should fallback gracefully and return string search results
        assert len(result) == 1
        assert "web-research" in result[0].text
