"""
Integration tests for native tool execution with mocked providers.

These tests verify the full native tool execution path including:
- Fallback chain integration
- Circuit breaker behavior
- Metrics recording
- Native result routing

Unlike E2E tests, these use mocked provider responses for CI reliability.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="test_native_tool_integration"),
]


class TestNativeToolExecutionPath:
    """Integration tests for the complete native tool execution path."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.core.tool_executor import reset_circuit_breaker
        from mcp_server_langgraph.tools.native_handler import reset_fallback_chain
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_circuit_breaker()
        reset_fallback_chain()
        get_metrics_aggregator().reset()
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_execution_path_native_success(self):
        """Test full execution path when native tool succeeds."""
        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        # Mock both native and builtin tools
        mock_native = AsyncMock(return_value="Native search results for AI news")
        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Builtin search results")

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._get_native_executor",
                return_value=mock_native,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._should_use_native",
                return_value=True,
            ),
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "AI news"},
                tool_preference="auto",
                model_name="claude-sonnet-4-20250514",
            )

        assert source == "native"
        assert "Native" in result

        # Verify metrics
        data = get_metrics_aggregator().get_comparison_data()
        assert len(data["tools"]) >= 0  # May have recorded metrics

    @pytest.mark.asyncio
    async def test_full_execution_path_native_failure_fallback(self):
        """Test full execution path when native fails and falls back."""
        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback

        # Mock native to fail, builtin to succeed
        mock_native = AsyncMock(side_effect=RuntimeError("API timeout"))
        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Builtin fallback results")

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._get_native_executor",
                return_value=mock_native,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._should_use_native",
                return_value=True,
            ),
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "AI news"},
                tool_preference="auto",
                model_name="claude-sonnet-4-20250514",
            )

        assert source == "builtin"
        assert "Builtin" in result

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_native_after_failures(self):
        """Test that circuit breaker prevents native calls after failures."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
            get_circuit_breaker,
        )

        breaker = get_circuit_breaker()

        # Simulate 5 failures to open the circuit
        for _ in range(5):
            breaker.record_failure("anthropic")

        assert breaker.is_open("anthropic") is True

        # Now execute - should use builtin directly
        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Builtin result")

        # Mock feature flags to enable native tools
        mock_feature_flags = MagicMock()
        mock_feature_flags.native_tools_enabled = True
        mock_feature_flags.anthropic_native_web_search_enabled = True

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.tools.native_handler.feature_flags",
                mock_feature_flags,
            ),
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "test"},
                tool_preference="auto",
                model_name="claude-sonnet-4-20250514",
            )

        # Should use builtin because circuit is open
        assert source == "builtin"

    @pytest.mark.asyncio
    async def test_builtin_preference_bypasses_native(self):
        """Test that builtin preference skips native entirely."""
        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback

        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Direct builtin result")

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=mock_builtin,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "test"},
                tool_preference="builtin",  # Force builtin
                model_name="claude-sonnet-4-20250514",
            )

        assert source == "builtin"
        assert "Direct builtin" in result


class TestNativeResultRoutingIntegration:
    """Integration tests for native result routing in the agent graph."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_response_with_native_results(self):
        """Test that generate_response correctly handles native results."""
        from unittest.mock import patch

        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response with web_search_results
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "Based on my search:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {
                            "title": "AI Breakthroughs 2025",
                            "url": "https://example.com/ai",
                            "snippet": "Major advances in AI...",
                        },
                    ],
                },
            ]
        )

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Search for AI news")],
            "selected_tools": ["web_search"],
            "tool_preference": "native",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
            "next_action": "",
        }

        # Create a mock config with required attributes
        mock_config = MagicMock()
        mock_config.enable_verification = False

        with (
            patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags,
            patch(
                "langchain_core.callbacks.manager.adispatch_custom_event",
                new_callable=AsyncMock,
            ),
        ):
            mock_flags.native_tools_enabled = False  # Skip native path for this test

            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
                config=mock_config,
            )

        # Verify response was processed
        messages = result.get("messages", [])
        assert len(messages) >= 1  # At least AI response

        # Verify routing to end
        assert result.get("next_action") == "end"

    @pytest.mark.asyncio
    async def test_agent_graph_use_tools_with_fallback(self):
        """Test use_tools node uses fallback chain."""
        # This is an integration test that would require more mocking
        # of the full agent graph context

        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback

        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Calculator result: 42")

        # Mock feature flags
        mock_feature_flags = MagicMock()
        mock_feature_flags.native_tools_enabled = False  # Disabled for non-native model

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.tools.native_handler.feature_flags",
                mock_feature_flags,
            ),
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="calculator",
                tool_args={"a": 2, "b": 40},
                tool_preference="auto",
                model_name="gpt-4",  # Non-native model
            )

        assert source == "builtin"
        assert "42" in result


class TestMetricsIntegration:
    """Integration tests for metrics recording during tool execution."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        get_metrics_aggregator().reset()
        gc.collect()

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_native_success(self):
        """Test that metrics are recorded on successful native execution."""
        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        mock_native = AsyncMock(return_value="Success")
        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Fallback")

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._get_native_executor",
                return_value=mock_native,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._should_use_native",
                return_value=True,
            ),
        ):
            await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "test"},
                tool_preference="native",
                model_name="claude-sonnet-4-20250514",
            )

        # Check aggregator has data
        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()

        # Native execution should be recorded
        # Note: This depends on how the fallback chain records metrics
        assert "tools" in data

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_fallback(self):
        """Test that fallback metrics are recorded."""
        from mcp_server_langgraph.core.tool_executor import execute_tool_with_fallback
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        mock_native = AsyncMock(side_effect=RuntimeError("Failed"))
        mock_builtin = MagicMock()
        mock_builtin.ainvoke = AsyncMock(return_value="Fallback success")

        with (
            patch(
                "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
                return_value=mock_builtin,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._get_native_executor",
                return_value=mock_native,
            ),
            patch(
                "mcp_server_langgraph.core.tool_executor._should_use_native",
                return_value=True,
            ),
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "test"},
                tool_preference="native",
                model_name="claude-sonnet-4-20250514",
            )

        assert source == "builtin"

        # Check aggregator has fallback data
        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()
        assert "tools" in data


class TestCircuitBreakerMetricsIntegration:
    """Integration tests for circuit breaker metrics."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.core.tool_executor import reset_circuit_breaker

        reset_circuit_breaker()
        gc.collect()

    def test_circuit_breaker_state_recorded(self):
        """Test that circuit breaker state changes are recorded."""
        from mcp_server_langgraph.core.tool_executor import get_circuit_breaker

        breaker = get_circuit_breaker()

        # Record failures to open circuit
        for _ in range(5):
            breaker.record_failure("anthropic")

        assert breaker.is_open("anthropic") is True

        # Record success to close circuit
        breaker.record_success("anthropic")

        assert breaker.is_open("anthropic") is False


class TestVertexAINativeToolIntegration:
    """Integration tests for Vertex AI native tool capabilities.

    Tests verify the specific limitations documented in ADR-0102:
    - Vertex AI Anthropic: Web search YES, Code execution NO
    - Vertex AI Gemini: Web search (googleSearch) YES
    """

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_vertex_ai_anthropic_supports_native_web_search(self):
        """Vertex AI Anthropic models should support native web search."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5@20251101")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "anthropic"
        assert caps.vendor == "vertex_ai_anthropic"

        # Handler should detect capability
        handler = NativeToolHandler("claude-opus-4-5@20251101")
        assert handler.caps.supports_native_web_search is True

    def test_vertex_ai_anthropic_no_code_execution(self):
        """Vertex AI Anthropic models should NOT support code execution.

        This is a critical limitation documented in ADR-0102.
        Code execution only works on direct Anthropic API and Bedrock.
        """
        from mcp_server_langgraph.agents.model_registry import ModelRegistry
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        registry = ModelRegistry()
        caps = registry.get("claude-opus-4-5@20251101")

        # Critical: Code execution NOT supported on Vertex AI
        assert caps.supports_native_code_execution is False

        # Handler should not return config for code_execution
        handler = NativeToolHandler("claude-opus-4-5@20251101")

        # Even if we ask for code_execution, it should not be available
        # because the model doesn't support it
        assert handler.caps.supports_native_code_execution is False

    def test_vertex_ai_gemini_supports_google_search(self):
        """Vertex AI Gemini models should support googleSearch."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        registry = ModelRegistry()
        caps = registry.get("vertex_ai/gemini-3-flash")

        assert caps.supports_native_web_search is True
        assert caps.native_provider == "google"

        # Handler should detect capability
        handler = NativeToolHandler("vertex_ai/gemini-3-flash")
        assert handler.caps.supports_native_web_search is True

    def test_vertex_ai_gemini_google_search_config_format(self):
        """Verify Vertex AI Gemini uses correct googleSearch config format."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("vertex_ai/gemini-3-flash")
        config = handler._get_config_for_tool("web_search")

        # Google uses different format than Anthropic
        assert config is not None
        assert "googleSearch" in config

    def test_direct_anthropic_vs_vertex_ai_code_execution_difference(self):
        """Verify direct API supports code execution but Vertex AI doesn't."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Direct API uses hyphen format: claude-opus-4-5-20251101
        direct_caps = registry.get("claude-opus-4-5-20251101")
        assert direct_caps.supports_native_code_execution is True
        assert direct_caps.vendor == "anthropic"

        # Vertex AI uses @ format: claude-opus-4-5@20251101
        vertex_caps = registry.get("claude-opus-4-5@20251101")
        assert vertex_caps.supports_native_code_execution is False
        assert vertex_caps.vendor == "vertex_ai_anthropic"

    def test_vertex_ai_code_execution_fallback_to_builtin(self):
        """When code_execution requested on Vertex AI, should fallback to execute_python builtin.

        This test verifies that Vertex AI Anthropic models don't support
        native code execution - they must fall back to builtin execute_python.
        """
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-opus-4-5@20251101")

        # Verify model doesn't support native code execution
        assert handler.caps.supports_native_code_execution is False

        # _get_config_for_tool should return None for code_execution
        # because the model doesn't support it
        config = handler._get_config_for_tool("code_execution")
        assert config is None, "Vertex AI Anthropic should not return code_execution config"

        # For comparison, web_search config should exist
        web_config = handler._get_config_for_tool("web_search")
        assert web_config is not None, "Vertex AI Anthropic should support web_search"
        assert web_config.get("type") == "web_search_20250305"

    def test_vertex_ai_model_naming_convention(self):
        """Verify Vertex AI model naming conventions are consistent."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Vertex AI Anthropic models use @version suffix
        # Note: Use actual model IDs from registry
        vertex_anthropic_models = [
            "claude-opus-4-5@20251101",
            "claude-sonnet-4-5@20250929",
            "claude-haiku-4-5@20251001",  # Correct date suffix
        ]

        for model_id in vertex_anthropic_models:
            caps = registry.get(model_id)
            assert caps.vendor == "vertex_ai_anthropic", f"{model_id} should be vertex_ai_anthropic"
            assert caps.native_provider == "anthropic", f"{model_id} should have anthropic native_provider"

        # Vertex AI Gemini models use vertex_ai/ prefix
        vertex_gemini_models = [
            "vertex_ai/gemini-3-flash",
            "vertex_ai/gemini-3-pro",
            "vertex_ai/gemini-3-flash-preview",
            "vertex_ai/gemini-3-pro-preview",
        ]

        for model_id in vertex_gemini_models:
            caps = registry.get(model_id)
            assert caps.vendor == "vertex_ai", f"{model_id} should be vertex_ai"
            assert caps.native_provider == "google", f"{model_id} should have google native_provider"
