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

    def test_openai_web_search_config(self) -> None:
        """Should return correct config for OpenAI web_search via Responses API."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "openai"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="gpt-5.2")
            config = handler._get_config_for_tool("web_search")

            assert config == {
                "type": "web_search_preview",
                "search_context_size": "medium",
            }

    def test_openai_code_interpreter_config(self) -> None:
        """Should return correct config for OpenAI code_interpreter via Responses API."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = "openai"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="gpt-5.2")
            config = handler._get_config_for_tool("code_execution")

            assert config == {
                "type": "code_interpreter",
                "container": {"type": "auto"},
            }


@pytest.mark.unit
class TestNativeToolHandlerOpenAIGating:
    """Tests for OpenAI native tool gating on Responses API flag."""

    def test_returns_true_for_openai_web_search_with_responses_api(self) -> None:
        """Should return True for OpenAI web_search when Responses API is enabled."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "openai"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="gpt-5.2")
                assert handler.should_use_native("web_search", "auto") is True

    def test_returns_false_for_openai_without_responses_api(self) -> None:
        """Should return False for OpenAI when Responses API is disabled."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = False  # Disabled!

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "openai"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="gpt-5.2")
                assert handler.should_use_native("web_search", "auto") is False

    def test_returns_true_for_openai_code_interpreter_with_responses_api(self) -> None:
        """Should return True for OpenAI code_interpreter when Responses API is enabled."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_code_interpreter_enabled = True
            mock_flags.use_responses_api_for_openai = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_code_execution = True
                mock_caps.native_provider = "openai"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="gpt-5.2")
                assert handler.should_use_native("code_execution", "auto") is True


@pytest.mark.unit
class TestNativeToolHandlerMCPPrefixPreservation:
    """Tests for MCP qualified name preservation in get_native_configs()."""

    def test_mcp_qualified_names_preserved_in_remaining(self) -> None:
        """MCP qualified names like 'github:create_issue' should be preserved intact."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "openai"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="gpt-5.2")
                native_configs, remaining = handler.get_native_configs(
                    ["github:create_issue", "web_search"], "auto"
                )

                # github:create_issue should be preserved intact
                assert "github:create_issue" in remaining
                # web_search should go to native
                assert len(native_configs) == 1

    def test_known_sources_are_parsed(self) -> None:
        """Known sources (native, builtin, mcp) should be parsed correctly."""
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
                    ["native:web_search", "builtin:calculator", "mcp:server/tool"], "auto"
                )

                # native:web_search goes to native_configs
                assert len(native_configs) == 1
                # builtin and mcp go to remaining
                assert "builtin:calculator" in remaining
                assert "mcp:server/tool" in remaining

    def test_plain_names_checked_for_native_in_auto_mode(self) -> None:
        """Plain tool names should be checked for native availability in auto mode."""
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
                    ["web_search", "calculator"], "auto"  # Plain names!
                )

                # web_search goes to native_configs
                assert len(native_configs) == 1
                # calculator goes to remaining
                assert "calculator" in remaining


@pytest.mark.unit
class TestParseNativeResultsOpenAI:
    """Tests for parse_native_results() with OpenAI Responses API output."""

    def test_parses_web_search_from_additional_kwargs(self) -> None:
        """Should parse web_search results from additional_kwargs['native_output']."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content="Here are the search results.",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "web_search_call",
                        "id": "ws_123",
                        "results": [
                            {"title": "Result 1", "url": "https://example.com/1", "snippet": "First result"},
                            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Second result"},
                        ],
                    }
                ]
            },
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].name == "web_search"
        assert "[Result 1]" in tool_messages[0].content
        assert "[Result 2]" in tool_messages[0].content

    def test_parses_code_interpreter_from_additional_kwargs(self) -> None:
        """Should parse code_interpreter results from additional_kwargs['native_output']."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content="The code executed successfully.",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "code_interpreter_call",
                        "id": "ci_456",
                        "output": "42",
                    }
                ]
            },
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].name == "code_execution"
        assert tool_messages[0].content == "42"

    def test_parses_nested_message_blocks(self) -> None:
        """Should parse tool results nested in message blocks."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content="Results from search.",
            additional_kwargs={
                "native_output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "web_search_call",
                                "id": "ws_nested",
                                "results": [
                                    {"title": "Nested Result", "url": "https://nested.com", "snippet": "Nested"},
                                ],
                            }
                        ],
                    }
                ]
            },
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].name == "web_search"
        assert "[Nested Result]" in tool_messages[0].content


@pytest.mark.unit
class TestNativeToolHandlerEdgeCases:
    """Edge case tests for NativeToolHandler.

    These tests cover edge cases identified during v7 implementation,
    particularly around capability checks and fallback behavior.
    """

    def test_get_config_returns_none_for_unsupported_web_search(self) -> None:
        """Should return None for web_search when model doesn't support it.

        This is critical for Vertex AI Anthropic models where web_search
        works but code_execution doesn't. The capability check must be
        performed before returning config.
        """
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.supports_native_web_search = False  # Unsupported!
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="some-model")
            config = handler._get_config_for_tool("web_search")

            assert config is None

    def test_get_config_returns_none_for_unsupported_code_execution(self) -> None:
        """Should return None for code_execution when model doesn't support it.

        Critical test for Vertex AI Anthropic where code_execution is NOT
        supported (ADR-0102). The capability check prevents returning a
        config that would fail at the provider.
        """
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.supports_native_web_search = True
            mock_caps.supports_native_code_execution = False  # Vertex AI limitation!
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="claude-opus-4-5@20251101")
            config = handler._get_config_for_tool("code_execution")

            assert config is None

    def test_get_native_configs_with_empty_list(self) -> None:
        """Should handle empty tool_ids list gracefully."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "anthropic"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
                native_configs, remaining = handler.get_native_configs([], "auto")

                assert native_configs == []
                assert remaining == []

    def test_get_native_configs_with_unknown_prefix(self) -> None:
        """Should preserve unknown prefixes in remaining list."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = True
                mock_caps.native_provider = "anthropic"
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
                native_configs, remaining = handler.get_native_configs(
                    ["unknown:some_tool", "custom:another_tool"], "auto"
                )

                assert native_configs == []
                assert "unknown:some_tool" in remaining
                assert "custom:another_tool" in remaining

    def test_model_with_no_native_provider(self) -> None:
        """Should return None for all configs when model has no native_provider."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.native_provider = None  # No provider!
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="unknown-model")
            web_config = handler._get_config_for_tool("web_search")
            code_config = handler._get_config_for_tool("code_execution")

            assert web_config is None
            assert code_config is None

    def test_execute_python_maps_to_code_execution(self) -> None:
        """Should map execute_python builtin name to code_execution.

        The native tool registry maps builtin names to native names.
        """
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.ModelRegistry"
        ) as mock_registry:
            mock_caps = MagicMock()
            mock_caps.supports_native_code_execution = True
            mock_caps.native_provider = "anthropic"
            mock_registry.return_value.get.return_value = mock_caps

            handler = NativeToolHandler(model_name="claude-opus-4-5-20251101")
            config = handler._get_config_for_tool("execute_python")

            assert config == {"type": "code_execution_20250825"}

    def test_fallback_for_native_only_with_unsupported_model(self) -> None:
        """Native-only preference with unsupported model should return empty configs.

        The agent graph handles logging the warning and using builtins.
        """
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        with patch(
            "mcp_server_langgraph.tools.native_handler.feature_flags"
        ) as mock_flags:
            mock_flags.native_tools_enabled = True

            with patch(
                "mcp_server_langgraph.tools.native_handler.ModelRegistry"
            ) as mock_registry:
                mock_caps = MagicMock()
                mock_caps.supports_native_web_search = False
                mock_caps.supports_native_code_execution = False
                mock_caps.native_provider = None
                mock_registry.return_value.get.return_value = mock_caps

                handler = NativeToolHandler(model_name="unknown-model")
                native_configs, remaining = handler.get_native_configs(
                    ["native:web_search"], "native"  # Force native
                )

                # No native configs available for unsupported model
                assert native_configs == []
                # The tool is left in remaining for fallback handling
                assert "native:web_search" in remaining
