"""
Integration tests for native LLM provider tools (v7).

Tests the full flow of native tool configuration, detection, and result parsing.
These tests verify the integration between:
- UnifiedToolRegistry (native tool registration)
- NativeToolHandler (should_use_native, get_native_configs)
- parse_native_results (AIMessage result extraction)
- Feature flags (native_tools_enabled, etc.)

Uses mocked LLM providers to avoid actual API calls.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="test_native_tools")]


@pytest.fixture
def mock_feature_flags():
    """Mock feature flags for native tools."""
    # Patch where it's imported in native_handler
    with patch("mcp_server_langgraph.tools.native_handler.feature_flags") as mock_ff:
        mock_ff.native_tools_enabled = True
        mock_ff.anthropic_native_web_search_enabled = True
        mock_ff.google_native_search_enabled = True
        mock_ff.anthropic_native_code_execution_enabled = True
        yield mock_ff


@pytest.fixture
def mock_model_registry():
    """Mock model registry with native tool capabilities."""
    # Patch where it's imported, not where it's defined
    with patch("mcp_server_langgraph.tools.native_handler.ModelRegistry") as MockRegistry:
        mock_caps = MagicMock()
        mock_caps.supports_native_web_search = True
        mock_caps.supports_native_code_execution = True
        mock_caps.native_provider = "anthropic"

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_caps
        MockRegistry.return_value = mock_instance
        yield MockRegistry


class TestNativeToolRegistration:
    """Tests for native tool registration in UnifiedToolRegistry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_native_tools_registered_at_startup(self, mock_feature_flags):
        """Native tools should be registered when registry initializes."""
        from mcp_server_langgraph.tools.unified_registry import (
            UnifiedToolRegistry,
            invalidate_registry,
        )

        # Clear existing registry
        invalidate_registry()

        # Create fresh registry (will initialize with native tools)
        registry = UnifiedToolRegistry()

        # Register native tools manually for this test
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        for (name, provider), defn in NATIVE_TOOLS.items():
            registry.register_native(
                name=defn.name,
                provider=defn.provider,
                provider_type=defn.provider_type,
                description=defn.description,
                fallback_builtin=defn.fallback_builtin,
            )

        # Verify native tools are registered
        native_tools = registry.filter_by_source("native")
        assert len(native_tools) > 0, "Expected native tools to be registered"

        # Check for web_search native tool (may be anthropic or google depending on iteration order)
        web_search = registry.get_by_id("native:web_search")
        assert web_search is not None, "Expected native:web_search to be registered"
        assert web_search.source == "native"
        assert web_search.provider in ("anthropic", "google")

    def test_native_tool_id_format(self, mock_feature_flags):
        """Native tool IDs should follow source:name format."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()
        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Test native tool",
        )

        tool = registry.get_by_id("native:web_search")
        assert tool is not None
        assert tool.tool_id == "native:web_search"
        assert tool.name == "web_search"
        assert tool.source == "native"


class TestNativeToolHandler:
    """Tests for NativeToolHandler functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_should_use_native_with_capable_model(
        self, mock_feature_flags, mock_model_registry
    ):
        """should_use_native should return True for capable models."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")
        result = handler.should_use_native("web_search", "auto")

        assert result is True

    def test_should_use_native_respects_preference(
        self, mock_feature_flags, mock_model_registry
    ):
        """should_use_native should respect builtin preference."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")

        # builtin preference should not use native
        result = handler.should_use_native("web_search", "builtin")
        assert result is False

        # mcp preference should not use native
        result = handler.should_use_native("web_search", "mcp")
        assert result is False

    def test_get_native_configs_separates_tools(
        self, mock_feature_flags, mock_model_registry
    ):
        """get_native_configs should separate native from non-native tool_ids."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")

        tool_ids = ["native:web_search", "builtin:calculator", "mcp:github:create_issue"]
        native_configs, remaining = handler.get_native_configs(tool_ids, "auto")

        assert len(native_configs) == 1
        assert native_configs[0]["type"] == "web_search_20250305"
        assert "builtin:calculator" in remaining
        assert "mcp:github:create_issue" in remaining


class TestNativeResultParsing:
    """Tests for parsing native tool results from AIMessage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_parse_native_results_extracts_web_search_results(self):
        """parse_native_results should extract web search result blocks."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.tools.native_handler import parse_native_results

        # Simulate Anthropic web search results in AIMessage content
        response = AIMessage(
            content=[
                {"type": "text", "text": "Here are the search results:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "AI News",
                            "url": "https://example.com/ai",
                            "snippet": "Latest AI developments",
                        }
                    ],
                },
            ]
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].name == "web_search"
        assert "AI News" in tool_messages[0].content

    def test_parse_native_results_handles_string_content(self):
        """parse_native_results should handle string content gracefully."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(content="Just a text response with no native results")

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 0

    def test_parse_native_results_extracts_tool_result_blocks(self):
        """parse_native_results should extract tool_result blocks."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_123",
                    "name": "code_execution",
                    "content": "Output: 42",
                }
            ]
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].tool_call_id == "toolu_123"
        assert tool_messages[0].name == "code_execution"


class TestNativeToolFeatureFlags:
    """Tests for feature flag integration with native tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_native_tools_disabled_by_default(self):
        """Native tools should be disabled when feature flag is off."""
        # Patch where it's used, not where it's defined
        with patch("mcp_server_langgraph.tools.native_handler.feature_flags") as mock_ff:
            mock_ff.native_tools_enabled = False

            from mcp_server_langgraph.tools.native_handler import NativeToolHandler

            handler = NativeToolHandler("claude-sonnet-4-20250514")
            result = handler.should_use_native("web_search", "auto")

            assert result is False

    def test_native_tools_require_provider_flag(self, mock_model_registry):
        """Native tools should require provider-specific flag."""
        # Patch where it's used, not where it's defined
        with patch("mcp_server_langgraph.tools.native_handler.feature_flags") as mock_ff:
            mock_ff.native_tools_enabled = True
            mock_ff.anthropic_native_web_search_enabled = False  # Disabled

            from mcp_server_langgraph.tools.native_handler import NativeToolHandler

            handler = NativeToolHandler("claude-sonnet-4-20250514")
            result = handler.should_use_native("web_search", "auto")

            assert result is False


class TestNativeToolIntegrationFlow:
    """End-to-end integration tests for native tool flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_native_tool_selection_to_execution_flow(
        self, mock_feature_flags, mock_model_registry
    ):
        """Test complete flow from tool selection to native result parsing."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.tools.native_handler import (
            NativeToolHandler,
            parse_native_results,
        )
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        # Setup: Create registry with native tools
        registry = UnifiedToolRegistry()
        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Search the web",
        )

        # Step 1: Resolve tool_ids to get native configs
        lc_tools, native_configs = registry.resolve_tool_ids(["native:web_search"])
        assert len(native_configs) == 1
        assert native_configs[0]["type"] == "web_search_20250305"

        # Step 2: Simulate LLM response with native results
        llm_response = AIMessage(
            content=[
                {"type": "text", "text": "I found these results:"},
                {
                    "type": "web_search_results",
                    "results": [{"title": "Test", "url": "https://test.com", "snippet": "Test result"}],
                },
            ]
        )

        # Step 3: Parse native results
        tool_messages = parse_native_results(llm_response)
        assert len(tool_messages) == 1
        assert tool_messages[0].name == "web_search"
