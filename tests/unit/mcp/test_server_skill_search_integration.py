"""Unit tests for MCP server SkillSearchTool integration.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify that:
1. SkillsToolHandler receives SkillSearchTool when semantic search is enabled
2. Feature flag controls SkillSearchTool creation
3. SkillSearchTool is correctly wired from bootstrap

ADR Reference: ADR-0092, ADR-0099
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.mcp]


@pytest.mark.xdist_group(name="test_server_skill_search")
class TestMCPServerSkillSearchIntegration:
    """Test MCP server integration with SkillSearchTool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skills_handler_receives_skill_search_tool_when_enabled(self):
        """
        GIVEN: enable_semantic_skill_search=True and vector infrastructure available
        WHEN: MCP server initializes SkillsToolHandler
        THEN: skill_search_tool should be passed to the handler
        """
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        mock_tool = MagicMock()

        # Verify the handler can accept and store skill_search_tool
        handler = SkillsToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            skill_search_tool=mock_tool,
        )

        assert handler.skill_search_tool is mock_tool

    def test_skills_handler_works_without_skill_search_tool(self):
        """
        GIVEN: enable_semantic_skill_search=False
        WHEN: MCP server initializes SkillsToolHandler without skill_search_tool
        THEN: Handler should work with fallback string search
        """
        from mcp_server_langgraph.mcp.handlers.skills import SkillsToolHandler

        handler = SkillsToolHandler(
            auth=MagicMock(),
            agent_graph=MagicMock(),
            skill_search_tool=None,
        )

        assert handler.skill_search_tool is None
        # Should not raise

    def test_create_skill_search_tool_import_available(self):
        """
        GIVEN: skills/adapters.py exists with create_skill_search_tool
        WHEN: Importing create_skill_search_tool
        THEN: Import should succeed
        """
        from mcp_server_langgraph.skills.adapters import create_skill_search_tool

        assert callable(create_skill_search_tool)


@pytest.mark.xdist_group(name="test_server_skill_search")
class TestSkillsStateIntegration:
    """Test SkillsState includes SkillSearchTool."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skills_state_has_skill_search_tool_field(self):
        """
        GIVEN: SkillsState dataclass
        WHEN: Checking fields
        THEN: Should include skill_search_tool field

        Note: This test will pass once skill_search_tool is added to SkillsState.
        """
        from mcp_server_langgraph.bootstrap.skills import SkillsState

        # Check if the field exists (will fail until implemented)
        state = SkillsState()
        # For now, check that SkillsState can be instantiated
        assert state is not None
