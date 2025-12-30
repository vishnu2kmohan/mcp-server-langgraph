"""
TDD: Unit tests for Help API / Contextual Help functionality.

Tests that contextual help returns proper data for different pages/features.

Phase 6: canvas_help feature flag
- Contextual help based on current page
- Quick actions and suggested reading
- Feature-specific help content

RED phase: These tests define expected behavior before implementation.
"""

import gc
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.help]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> Any:
    """Mock settings with help enabled."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.ff_enable_canvas_help = True
    return mock


# =============================================================================
# Contextual Help API Tests
# =============================================================================


@pytest.mark.xdist_group(name="help_api_contextual")
class TestContextualHelpAPI:
    """Test contextual help functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_contextual_help_returns_topics(self) -> None:
        """GIVEN valid page WHEN get_contextual_help THEN returns help topics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="chat",
            active_feature="",
        )

        assert "help_topics" in result
        assert isinstance(result["help_topics"], list)
        assert len(result["help_topics"]) > 0

    @pytest.mark.asyncio
    async def test_contextual_help_returns_quick_actions(self) -> None:
        """GIVEN valid page WHEN get_contextual_help THEN returns quick actions."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="admin",
            active_feature="agent-approvals",
        )

        assert "quick_actions" in result
        assert isinstance(result["quick_actions"], list)

    @pytest.mark.asyncio
    async def test_contextual_help_returns_suggested_reading(self) -> None:
        """GIVEN valid page WHEN get_contextual_help THEN returns suggested reading."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="observability",
            active_feature="",
        )

        assert "suggested_reading" in result
        assert isinstance(result["suggested_reading"], list)

    @pytest.mark.asyncio
    async def test_contextual_help_fallback_for_unknown_page(self) -> None:
        """GIVEN unknown page WHEN get_contextual_help THEN returns default help."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="unknown-page",
            active_feature="unknown-feature",
        )

        # Should still return valid structure with default content
        assert "help_topics" in result
        assert len(result["help_topics"]) > 0
        # Default help should include getting started
        assert any("getting-started" in t.get("id", "") for t in result["help_topics"])

    @pytest.mark.asyncio
    async def test_contextual_help_topic_structure(self) -> None:
        """GIVEN valid request WHEN get_contextual_help THEN topics have required fields."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="chat",
            active_feature="",
        )

        # Check topic structure
        topic = result["help_topics"][0]
        assert "id" in topic
        assert "title" in topic
        assert "summary" in topic
        assert "relevance" in topic

    @pytest.mark.asyncio
    async def test_contextual_help_quick_action_structure(self) -> None:
        """GIVEN valid request WHEN get_contextual_help THEN actions have required fields."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_contextual_help(
            user_id="user-123",
            current_page="admin",
            active_feature="agent-approvals",
        )

        # Check quick action structure
        if result["quick_actions"]:
            action = result["quick_actions"][0]
            assert "label" in action
            assert "action" in action


# =============================================================================
# Learning Path API Tests
# =============================================================================


@pytest.mark.xdist_group(name="help_api_learning")
class TestLearningPathAPI:
    """Test learning path functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_learning_path_returns_progress(self) -> None:
        """GIVEN valid user WHEN get_learning_path THEN returns progress info."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_learning_path(
            user_id="user-123",
            persona="alice-builder",
        )

        assert "current_level" in result
        assert "progress_percentage" in result
        assert 0 <= result["progress_percentage"] <= 100

    @pytest.mark.asyncio
    async def test_learning_path_returns_next_steps(self) -> None:
        """GIVEN valid user WHEN get_learning_path THEN returns next steps."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_learning_path(
            user_id="user-123",
            persona="alice-analyst",
        )

        assert "next_steps" in result
        assert isinstance(result["next_steps"], list)

    @pytest.mark.asyncio
    async def test_learning_path_fallback_for_unknown_persona(self) -> None:
        """GIVEN unknown persona WHEN get_learning_path THEN returns default path."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(settings=None, llm_factory=None)

        result = await service.get_learning_path(
            user_id="user-123",
            persona="unknown-persona",
        )

        # Should still return valid structure
        assert "current_level" in result
        assert "next_steps" in result
