"""
Tests for OpenTelemetry GenAI Semantic Conventions in LLM operations.

TDD tests to ensure LLM spans use OTEL semantic conventions:
- gen_ai.system: The GenAI provider (e.g., "openai", "anthropic")
- gen_ai.request.model: The model name
- gen_ai.request.temperature: The temperature setting
- gen_ai.request.max_tokens: The max tokens setting
- gen_ai.usage.input_tokens: Input token count
- gen_ai.usage.output_tokens: Output token count

Reference: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
"""

import gc
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group(name="genai_semantic_conventions"),
]


@pytest.mark.xdist_group(name="genai_semantic_conventions")
class TestGenAISemanticConventions:
    """Test suite for GenAI semantic conventions in LLM spans."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_llm_response(self) -> MagicMock:
        """Create a mock LiteLLM response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message = MagicMock()
        response.choices[0].message.content = "Test response"
        response.usage = MagicMock()
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 20
        response.usage.total_tokens = 30
        return response

    @pytest.fixture
    def captured_attributes(self) -> dict[str, str | int | float]:
        """Container for captured span attributes."""
        return {}

    @pytest.fixture
    def mock_telemetry(self, captured_attributes: dict[str, str | int | float]) -> MagicMock:
        """Create a mock telemetry with tracer that captures attributes."""
        mock_span = MagicMock()
        mock_span.set_attribute = lambda k, v: captured_attributes.update({k: v})

        @contextmanager
        def mock_start_span(name: str):
            yield mock_span

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span = mock_start_span

        mock_telemetry = MagicMock()
        mock_telemetry.tracer = mock_tracer
        mock_telemetry.logger = MagicMock()
        mock_telemetry.metrics = MagicMock()
        mock_telemetry.metrics.successful_calls = MagicMock()
        mock_telemetry.metrics.failed_calls = MagicMock()

        return mock_telemetry

    @pytest.mark.asyncio
    async def test_llm_span_includes_gen_ai_system(
        self,
        mock_llm_response: MagicMock,
        mock_telemetry: MagicMock,
        captured_attributes: dict[str, str | int | float],
    ) -> None:
        """
        GIVEN an LLM factory with a provider configured
        WHEN ainvoke() is called
        THEN the span should include gen_ai.system attribute with the provider name
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration"),
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage"),
        ):
            mock_acompletion.return_value = mock_llm_response

            factory = LLMFactory(
                provider="openai",
                model_name="gpt-4",
                api_key="test-key",
                telemetry=mock_telemetry,
            )

            await factory.ainvoke([HumanMessage(content="Test")])

        assert "gen_ai.system" in captured_attributes
        assert captured_attributes["gen_ai.system"] == "openai"

    @pytest.mark.asyncio
    async def test_llm_span_includes_gen_ai_request_model(
        self,
        mock_llm_response: MagicMock,
        mock_telemetry: MagicMock,
        captured_attributes: dict[str, str | int | float],
    ) -> None:
        """
        GIVEN an LLM factory with a model configured
        WHEN ainvoke() is called
        THEN the span should include gen_ai.request.model attribute
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration"),
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage"),
        ):
            mock_acompletion.return_value = mock_llm_response

            factory = LLMFactory(
                provider="anthropic",
                model_name="claude-3-opus-20240229",
                api_key="test-key",
                telemetry=mock_telemetry,
            )

            await factory.ainvoke([HumanMessage(content="Test")])

        assert "gen_ai.request.model" in captured_attributes
        assert captured_attributes["gen_ai.request.model"] == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_llm_span_includes_gen_ai_token_usage(
        self,
        mock_llm_response: MagicMock,
        mock_telemetry: MagicMock,
        captured_attributes: dict[str, str | int | float],
    ) -> None:
        """
        GIVEN an LLM response with token usage
        WHEN ainvoke() completes
        THEN the span should include gen_ai.usage.input_tokens and gen_ai.usage.output_tokens
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration"),
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage"),
        ):
            mock_acompletion.return_value = mock_llm_response

            factory = LLMFactory(
                provider="openai",
                model_name="gpt-4",
                api_key="test-key",
                telemetry=mock_telemetry,
            )

            await factory.ainvoke([HumanMessage(content="Test")])

        assert "gen_ai.usage.input_tokens" in captured_attributes
        assert captured_attributes["gen_ai.usage.input_tokens"] == 10
        assert "gen_ai.usage.output_tokens" in captured_attributes
        assert captured_attributes["gen_ai.usage.output_tokens"] == 20

    @pytest.mark.asyncio
    async def test_llm_span_includes_legacy_attributes_for_backward_compat(
        self,
        mock_llm_response: MagicMock,
        mock_telemetry: MagicMock,
        captured_attributes: dict[str, str | int | float],
    ) -> None:
        """
        GIVEN an LLM factory
        WHEN ainvoke() is called
        THEN the span should include both gen_ai.* and legacy llm.* attributes
        for backward compatibility during migration period
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration"),
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage"),
        ):
            mock_acompletion.return_value = mock_llm_response

            factory = LLMFactory(
                provider="openai",
                model_name="gpt-4",
                api_key="test-key",
                telemetry=mock_telemetry,
            )

            await factory.ainvoke([HumanMessage(content="Test")])

        # New OTEL semantic conventions
        assert "gen_ai.system" in captured_attributes
        assert "gen_ai.request.model" in captured_attributes

        # Legacy attributes for backward compatibility
        assert "llm.provider" in captured_attributes
        assert "llm.model" in captured_attributes
