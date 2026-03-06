"""
Tests for Short-Form Tool Descriptions.

Phase 3.1 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Short-form tool descriptions reduce token usage by ~40%
by providing three levels of description detail.

Tests cover:
1. ToolDescription data model
2. Feature flags for short descriptions
3. Description level selection
4. Token savings estimation
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.mcp
class TestToolDescriptionModel:
    """Test ToolDescription data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_description_exists(self) -> None:
        """ToolDescription model should exist."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        assert ToolDescription is not None

    def test_tool_description_has_required_fields(self) -> None:
        """ToolDescription should have name and descriptions."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="chat",
            description_short="Chat with AI agent",
            description_medium="Chat with AI agent. Supports text messages.",
            description_full="Chat with AI agent. Supports text messages, "
            "file attachments, and streaming responses. "
            "Rate limited to 100 requests per minute.",
        )

        assert desc.name == "chat"
        assert desc.description_short == "Chat with AI agent"
        assert "Supports text messages" in desc.description_medium
        assert "Rate limited" in desc.description_full

    def test_tool_description_get_description_short(self) -> None:
        """get_description('short') should return short description."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="Short desc",
            description_medium="Medium description here",
            description_full="Full description with all details",
        )

        result = desc.get_description("short")
        assert result == "Short desc"

    def test_tool_description_get_description_medium(self) -> None:
        """get_description('medium') should return medium description."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="Short desc",
            description_medium="Medium description here",
            description_full="Full description with all details",
        )

        result = desc.get_description("medium")
        assert result == "Medium description here"

    def test_tool_description_get_description_full(self) -> None:
        """get_description('full') should return full description."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="Short desc",
            description_medium="Medium description here",
            description_full="Full description with all details",
        )

        result = desc.get_description("full")
        assert result == "Full description with all details"

    def test_tool_description_get_description_default(self) -> None:
        """get_description() without level should return short by default."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="Short desc",
            description_medium="Medium description here",
            description_full="Full description with all details",
        )

        result = desc.get_description()
        assert result == "Short desc"


@pytest.mark.unit
@pytest.mark.mcp
class TestToolDescriptionFeatureFlags:
    """Test feature flags for tool descriptions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_short_tool_descriptions_flag_exists(self) -> None:
        """Feature flags should include enable_short_tool_descriptions."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_short_tool_descriptions")

    def test_enable_short_tool_descriptions_default_true(self) -> None:
        """enable_short_tool_descriptions should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_short_tool_descriptions is True


@pytest.mark.unit
@pytest.mark.mcp
class TestToolDescriptionRegistry:
    """Test ToolDescriptionRegistry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_description_registry_exists(self) -> None:
        """ToolDescriptionRegistry class should exist."""
        from mcp_server_langgraph.mcp.tool_descriptions import (
            ToolDescriptionRegistry,
        )

        assert ToolDescriptionRegistry is not None

    def test_tool_description_registry_register(self) -> None:
        """Registry should allow registering tool descriptions."""
        from mcp_server_langgraph.mcp.tool_descriptions import (
            ToolDescription,
            ToolDescriptionRegistry,
        )

        registry = ToolDescriptionRegistry()
        desc = ToolDescription(
            name="test_tool",
            description_short="Short",
            description_medium="Medium",
            description_full="Full",
        )
        registry.register(desc)

        assert registry.get("test_tool") is not None

    def test_tool_description_registry_get_description(self) -> None:
        """Registry should return description at requested level."""
        from mcp_server_langgraph.mcp.tool_descriptions import (
            ToolDescription,
            ToolDescriptionRegistry,
        )

        registry = ToolDescriptionRegistry()
        desc = ToolDescription(
            name="my_tool",
            description_short="Quick summary",
            description_medium="Detailed summary",
            description_full="Very detailed explanation",
        )
        registry.register(desc)

        result = registry.get_description("my_tool", "short")
        assert result == "Quick summary"

    def test_tool_description_registry_get_missing_returns_none(self) -> None:
        """Registry should return None for unregistered tools."""
        from mcp_server_langgraph.mcp.tool_descriptions import (
            ToolDescriptionRegistry,
        )

        registry = ToolDescriptionRegistry()
        result = registry.get("nonexistent_tool")
        assert result is None


@pytest.mark.unit
@pytest.mark.mcp
class TestToolDescriptionTokenSavings:
    """Test token savings estimation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_description_estimate_tokens(self) -> None:
        """ToolDescription should estimate token count."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="A" * 40,  # ~10 tokens
            description_medium="B" * 200,  # ~50 tokens
            description_full="C" * 600,  # ~150 tokens
        )

        short_tokens = desc.estimate_tokens("short")
        full_tokens = desc.estimate_tokens("full")

        # Short should be significantly less than full
        assert short_tokens < full_tokens
        assert short_tokens < 20
        assert full_tokens > 100

    def test_tool_description_savings_percentage(self) -> None:
        """Should calculate savings percentage between levels."""
        from mcp_server_langgraph.mcp.tool_descriptions import ToolDescription

        desc = ToolDescription(
            name="test",
            description_short="Short",  # ~2 tokens
            description_medium="M" * 100,  # ~25 tokens
            description_full="F" * 400,  # ~100 tokens
        )

        savings = desc.savings_percentage("short", "full")

        # Short should save at least 80% vs full
        assert savings > 80


@pytest.mark.unit
@pytest.mark.mcp
class TestDetailLevelSelector:
    """Test detail level selection based on context budget."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_detail_level_full_when_ample_budget(self) -> None:
        """Should return 'full' when context budget is ample."""
        from mcp_server_langgraph.mcp.tool_descriptions import get_detail_level

        # Budget is percentage used (0-1), lower = more available
        level = get_detail_level(context_usage=0.2)  # 20% used
        assert level == "full"

    def test_get_detail_level_medium_when_moderate_budget(self) -> None:
        """Should return 'medium' when context budget is moderate."""
        from mcp_server_langgraph.mcp.tool_descriptions import get_detail_level

        level = get_detail_level(context_usage=0.5)  # 50% used
        assert level == "medium"

    def test_get_detail_level_short_when_tight_budget(self) -> None:
        """Should return 'short' when context budget is tight."""
        from mcp_server_langgraph.mcp.tool_descriptions import get_detail_level

        level = get_detail_level(context_usage=0.8)  # 80% used
        assert level == "short"

    def test_get_detail_level_minimal_when_critical(self) -> None:
        """Should return 'minimal' when context budget is critical."""
        from mcp_server_langgraph.mcp.tool_descriptions import get_detail_level

        level = get_detail_level(context_usage=0.95)  # 95% used
        assert level == "minimal"
