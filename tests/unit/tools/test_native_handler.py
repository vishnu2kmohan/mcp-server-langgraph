"""
Tests for tools/native_handler.py module.

TDD: These tests define the expected behavior for native tool configuration
and result parsing.
"""

from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage


@pytest.mark.unit
class TestNativeToolHandlerShouldUseNative:
    """Tests for should_use_native() method."""

    def test_returns_false_when_feature_disabled(self) -> None:
        """Should return False when native_tools_enabled is False."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = False

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            assert handler.should_use_native("web_search", "auto") is False

    def test_returns_false_for_builtin_preference(self) -> None:
        """Should return False when preference is 'builtin'."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            assert handler.should_use_native("web_search", "builtin") is False

    def test_returns_false_for_mcp_preference(self) -> None:
        """Should return False when preference is 'mcp'."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            assert handler.should_use_native("web_search", "mcp") is False

    def test_returns_true_for_web_search_with_capable_model(self) -> None:
        """Should return True for web_search with capable Anthropic model."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.anthropic_native_web_search_enabled = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "anthropic"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
                assert handler.should_use_native("web_search", "auto") is True


@pytest.mark.unit
class TestNativeToolHandlerGetNativeConfigs:
    """Tests for get_native_configs() method."""

    def test_separates_native_from_builtin_tool_ids(self) -> None:
        """Should separate native configs from remaining tool_ids."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.anthropic_native_web_search_enabled = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "anthropic"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
                native_configs, remaining = handler.get_native_configs(
                    ["native:web_search", "builtin:calculator"], "auto"
                )

                assert len(native_configs) == 1
                assert native_configs[0]["type"] == "web_search_20250305"
                assert remaining == ["builtin:calculator"]


@pytest.mark.unit
class TestParseNativeResults:
    """Tests for parse_native_results() function."""

    def test_returns_empty_list_for_string_content(self) -> None:
        """Should return empty list when content is a string."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(content="Regular response")
        results = parse_native_results(response)

        assert results == []

    def test_parses_tool_result_blocks(self) -> None:
        """Should parse tool_result content blocks."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {"type": "text", "text": "Here are the results:"},
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_123",
                    "name": "web_search",
                    "content": "Search results here",
                },
            ]
        )
        results = parse_native_results(response)

        assert len(results) == 1
        assert results[0].tool_call_id == "toolu_123"
        assert results[0].name == "web_search"
        assert results[0].content == "Search results here"

    def test_parses_web_search_results_blocks(self) -> None:
        """Should parse web_search_results content blocks."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "Test Result",
                            "url": "https://example.com",
                            "snippet": "This is a snippet",
                        }
                    ],
                }
            ]
        )
        results = parse_native_results(response)

        assert len(results) == 1
        assert results[0].name == "web_search"
        assert "Test Result" in results[0].content
        assert "https://example.com" in results[0].content


@pytest.mark.unit
class TestNativeToolHandlerGetConfigForTool:
    """Tests for _get_config_for_tool() method."""

    def test_anthropic_web_search_config(self) -> None:
        """Should return correct config for Anthropic web_search."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            config = handler._get_config_for_tool("web_search")

            assert config == {"type": "web_search_20250305"}

    def test_anthropic_code_execution_config(self) -> None:
        """Should return correct config for Anthropic code_execution."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            config = handler._get_config_for_tool("code_execution")

            assert config == {"type": "code_execution_20250825"}

    def test_google_web_search_config(self) -> None:
        """Should return correct config for Google grounded search."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "google"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="gemini-2.5-flash")
            config = handler._get_config_for_tool("web_search")

            assert config == {"googleSearch": {}}

    def test_unsupported_tool_returns_none(self) -> None:
        """Should return None for unsupported tools."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
            config = handler._get_config_for_tool("calculator")

            assert config is None
