"""Tests for SkillSearchTool semantic skill discovery.

TDD: These tests define the contract for the SkillSearchTool that
provides semantic skill discovery via vector similarity.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestSkillSearchToolBasic:
    """Tests for SkillSearchTool basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skill_search_tool_exists(self) -> None:
        """Test SkillSearchTool class exists."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        assert SkillSearchTool is not None

    def test_skill_search_tool_accepts_vector_provider(self) -> None:
        """Test SkillSearchTool accepts vector provider."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        tool = SkillSearchTool(vector_provider=mock_provider)

        assert tool.vector_provider is mock_provider

    def test_skill_search_tool_has_search_method(self) -> None:
        """Test SkillSearchTool has search method."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        tool = SkillSearchTool(vector_provider=mock_provider)

        assert hasattr(tool, "search")

    def test_skill_search_tool_has_index_skill_method(self) -> None:
        """Test SkillSearchTool has index_skill method."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        tool = SkillSearchTool(vector_provider=mock_provider)

        assert hasattr(tool, "index_skill")

    def test_skill_search_tool_has_collection_name(self) -> None:
        """Test SkillSearchTool has COLLECTION constant."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        assert hasattr(SkillSearchTool, "COLLECTION")
        assert SkillSearchTool.COLLECTION == "skills"


@pytest.mark.unit
class TestSkillSearchToolIndex:
    """Tests for SkillSearchTool indexing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_index_skill_calls_embedding_service(self) -> None:
        """Test index_skill calls embedding service."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        skill = Skill(name="test-skill", description="A test skill")
        await tool.index_skill(skill, skill_id="skill-123")

        mock_embeddings.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_skill_calls_upsert(self) -> None:
        """Test index_skill calls vector provider upsert."""
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        skill = Skill(name="test-skill", description="A test skill", tags=["test", "demo"])
        await tool.index_skill(skill, skill_id="skill-123")

        mock_provider.upsert.assert_called_once()
        call_args = mock_provider.upsert.call_args
        assert call_args[1]["collection"] == "skills"
        assert call_args[1]["id"] == "skill-123"


@pytest.mark.unit
class TestSkillSearchToolSearch:
    """Tests for SkillSearchTool search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        """Test search returns list of results."""
        from mcp_server_langgraph.skills.search import SkillSearchResult, SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(
            return_value=[
                {"id": "skill-1", "score": 0.9, "metadata": {"name": "skill-one"}},
            ]
        )
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        results = await tool.search("find code review skill")

        assert len(results) >= 1
        assert isinstance(results[0], SkillSearchResult)

    @pytest.mark.asyncio
    async def test_search_embeds_query(self) -> None:
        """Test search embeds the query string."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(return_value=[])
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        await tool.search("find test skill")

        mock_embeddings.embed.assert_called_with("find test skill")

    @pytest.mark.asyncio
    async def test_search_respects_limit(self) -> None:
        """Test search respects limit parameter."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(return_value=[])
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        await tool.search("find skill", limit=5)

        call_args = mock_provider.search.call_args
        assert call_args[1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_respects_min_score(self) -> None:
        """Test search respects min_score parameter."""
        from mcp_server_langgraph.skills.search import SkillSearchTool

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(return_value=[])
        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SkillSearchTool(vector_provider=mock_provider, embedding_service=mock_embeddings)

        await tool.search("find skill", min_score=0.8)

        call_args = mock_provider.search.call_args
        assert call_args[1]["min_score"] == 0.8


@pytest.mark.unit
class TestSkillSearchResult:
    """Tests for SkillSearchResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skill_search_result_exists(self) -> None:
        """Test SkillSearchResult dataclass exists."""
        from mcp_server_langgraph.skills.search import SkillSearchResult

        assert SkillSearchResult is not None

    def test_skill_search_result_has_fields(self) -> None:
        """Test SkillSearchResult has required fields."""
        from mcp_server_langgraph.skills.search import SkillSearchResult

        result = SkillSearchResult(
            skill_id="skill-123",
            name="test-skill",
            description="A test skill",
            score=0.95,
        )

        assert result.skill_id == "skill-123"
        assert result.name == "test-skill"
        assert result.description == "A test skill"
        assert result.score == 0.95

    def test_skill_search_result_has_optional_tags(self) -> None:
        """Test SkillSearchResult has optional tags field."""
        from mcp_server_langgraph.skills.search import SkillSearchResult

        result = SkillSearchResult(
            skill_id="skill-123",
            name="test-skill",
            description="A test skill",
            score=0.95,
            tags=["test", "demo"],
        )

        assert result.tags == ["test", "demo"]
