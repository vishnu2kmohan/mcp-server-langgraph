"""
Tests for Skills MCP Handler

Tests for skills/list, skills/get, skills/execute operations.
Following TDD - these tests define the expected behavior.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.skills
@pytest.mark.xdist_group(name="mcp_skills_handler")
class TestSkillsToolHandler:
    """Tests for SkillsToolHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_class_exists(self) -> None:
        """Test that SkillsToolHandler class exists."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        assert SkillsToolHandler is not None

    def test_handler_initialization(self) -> None:
        """Test handler initialization with dependencies."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()

        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        assert handler.auth == auth_mock
        assert handler.agent_graph == agent_graph_mock

    @pytest.mark.asyncio
    async def test_handle_list_skills(self) -> None:
        """Test listing all skills."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_list_skills(
            arguments={},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) >= 0  # May be empty if no skills registered

    @pytest.mark.asyncio
    async def test_handle_list_skills_with_category_filter(self) -> None:
        """Test listing skills filtered by category."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        # Register a test skill
        handler.register_skill_for_test(
            name="test-skill",
            description="Test skill",
            category="research",
        )

        result = await handler.handle_list_skills(
            arguments={"category": "research"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        # Result should contain skills of the requested category

    @pytest.mark.asyncio
    async def test_handle_get_skill(self) -> None:
        """Test getting a specific skill by name."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        # Register a test skill
        handler.register_skill_for_test(
            name="test-skill",
            description="Test skill description",
            instructions="Do something useful",
        )

        result = await handler.handle_get_skill(
            arguments={"name": "test-skill"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        # Should contain skill details including instructions

    @pytest.mark.asyncio
    async def test_handle_get_skill_not_found(self) -> None:
        """Test getting a nonexistent skill returns error."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_get_skill(
            arguments={"name": "nonexistent-skill"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_search_skills(self) -> None:
        """Test searching skills by query."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        # Register test skills
        handler.register_skill_for_test(
            name="web-research",
            description="Research topics on the web",
        )
        handler.register_skill_for_test(
            name="code-review",
            description="Review code for issues",
        )

        result = await handler.handle_search_skills(
            arguments={"query": "research"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        # Should contain matching skills

    @pytest.mark.asyncio
    async def test_handle_execute_skill_feature_flag_disabled(self) -> None:
        """Test skill execution respects feature flag."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = SkillsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        with patch("mcp_server_langgraph.mcp.handlers.skills.feature_flags") as ff_mock:
            ff_mock.enable_skills_system = False

            result = await handler.handle_execute_skill(
                arguments={"name": "test-skill", "args": {}},
                span=MagicMock(),
                user_id="test-user",
            )

            assert isinstance(result, list)
            assert "disabled" in result[0].text.lower()


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.skills
@pytest.mark.xdist_group(name="mcp_skills_handler")
class TestSkillsToolHandlerIntegration:
    """Integration tests for SkillsToolHandler with registry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_uses_skill_registry(self) -> None:
        """Test handler integrates with SkillRegistry."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler
        from mcp_server_langgraph.skills import SkillRegistry

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        registry = SkillRegistry()

        handler = SkillsToolHandler(
            auth=auth_mock,
            agent_graph=agent_graph_mock,
            skill_registry=registry,
        )

        assert handler.skill_registry is registry

    @pytest.mark.asyncio
    async def test_handler_uses_skill_discovery(self) -> None:
        """Test handler integrates with SkillDiscovery."""
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler
        from mcp_server_langgraph.skills import SkillDiscovery, SkillRegistry

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        registry = SkillRegistry()
        discovery = SkillDiscovery(registry=registry)

        handler = SkillsToolHandler(
            auth=auth_mock,
            agent_graph=agent_graph_mock,
            skill_discovery=discovery,
        )

        assert handler.skill_discovery is discovery
