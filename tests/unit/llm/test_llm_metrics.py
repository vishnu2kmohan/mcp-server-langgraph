"""
TDD tests for LLM metrics instrumentation.

Verifies that LLM operations record token usage and duration metrics.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.llm
@pytest.mark.metrics
@pytest.mark.xdist_group(name="llm_metrics")
class TestLLMMetrics:
    """Test LLM metrics instrumentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_records_token_usage_metrics(self) -> None:
        """Verify async LLM invocation records token usage metrics."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            temperature=0.7,
            max_tokens=1000,
        )

        # Mock LiteLLM response with usage data
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 150

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage") as mock_token_usage,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration") as mock_duration,
        ):
            mock_acompletion.return_value = mock_response

            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify token usage metrics were recorded
            mock_token_usage.assert_called_once()
            call_args = mock_token_usage.call_args

            # Check model is passed
            assert call_args.kwargs.get("model") == "gemini-2.5-flash" or call_args[0][0] == "gemini-2.5-flash"
            # Check prompt tokens
            assert call_args.kwargs.get("prompt_tokens") == 50 or call_args[0][1] == 50
            # Check completion tokens
            assert call_args.kwargs.get("completion_tokens") == 100 or call_args[0][2] == 100

            # Verify duration metrics were recorded
            mock_duration.assert_called_once()

    @pytest.mark.asyncio
    async def test_ainvoke_records_duration_metrics(self) -> None:
        """Verify async LLM invocation records request duration."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-5",
            temperature=0.5,
        )

        # Mock LiteLLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage"),
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration") as mock_duration,
        ):
            mock_acompletion.return_value = mock_response

            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify duration metrics were recorded with model
            mock_duration.assert_called_once()
            call_args = mock_duration.call_args

            # Check model is passed
            assert "gpt-5" in str(call_args)
            # Check duration is positive
            duration = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("duration_ms")
            assert isinstance(duration, float)
            assert duration >= 0

    def test_invoke_records_token_usage_metrics(self) -> None:
        """Verify sync LLM invocation records token usage metrics."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-sonnet-4-5",
            temperature=0.3,
        )

        # Mock LiteLLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 75
        mock_response.usage.total_tokens = 100

        with (
            patch("mcp_server_langgraph.llm.factory.completion") as mock_completion,
            patch("mcp_server_langgraph.llm.factory.record_llm_token_usage") as mock_token_usage,
            patch("mcp_server_langgraph.llm.factory.record_llm_request_duration") as mock_duration,
        ):
            mock_completion.return_value = mock_response

            factory.invoke([{"role": "user", "content": "Hello"}])

            # Verify token usage metrics were recorded
            mock_token_usage.assert_called_once()

            # Verify duration metrics were recorded
            mock_duration.assert_called_once()
