"""
Tests for OpenAI Native Tools Error Handling (v26).

Validates that OpenAI native tools require use_responses_api_for_openai=True.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.llm]


@pytest.fixture
def mock_telemetry():
    """Create mock telemetry for LLMFactory."""
    telemetry = MagicMock()
    telemetry.tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    telemetry.tracer.start_as_current_span.return_value = mock_span
    return telemetry


@pytest.mark.xdist_group(name="test_openai_native_tools")
class TestOpenAINativeToolsValidation:
    """Tests for OpenAI native tools validation (v26)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_raises_valueerror_for_openai_native_tools_without_responses_api(self, mock_telemetry):
        """OpenAI native_tools without Responses API raises ValueError."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Mock feature_flags to disable Responses API
        with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_feature_flags:
            mock_feature_flags.use_responses_api_for_openai = False
            mock_feature_flags.enable_llm_hooks = False
            mock_feature_flags.adaptive_concurrency = False
            mock_feature_flags.adaptive_timeout = False
            mock_feature_flags.adaptive_retry = False
            mock_feature_flags.enable_llm_token_counting = False

            with pytest.raises(ValueError, match="use_responses_api_for_openai"):
                await factory.ainvoke(
                    messages=[{"role": "user", "content": "Hello"}],
                    native_tools=[{"type": "code_interpreter"}],
                )

    @pytest.mark.asyncio
    async def test_ainvoke_succeeds_for_openai_native_tools_with_responses_api(self, mock_telemetry):
        """OpenAI native_tools with Responses API enabled does not raise ValueError.

        This test verifies that when use_responses_api_for_openai=True,
        the v26 validation does not raise ValueError. The actual LLM call
        is mocked to avoid resilience/retry complexity.
        """

        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Mock feature_flags to enable Responses API
        with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_feature_flags:
            mock_feature_flags.use_responses_api_for_openai = True

            # Test that validation passes (no ValueError raised)
            # We use an early return by mocking the entire method after validation
            # The key point is: no ValueError should be raised for the validation check
            try:
                # Just call to trigger validation - we expect it to pass
                # and then fail later (which is fine for this test)
                await factory.ainvoke(
                    messages=[{"role": "user", "content": "Hello"}],
                    native_tools=[{"type": "code_interpreter"}],
                )
            except ValueError as e:
                if "use_responses_api_for_openai" in str(e):
                    pytest.fail("Should not raise ValueError when Responses API is enabled")
                # Re-raise if it's a different ValueError
                raise
            except Exception:
                # Any other exception is fine - validation passed
                pass

    @pytest.mark.asyncio
    async def test_ainvoke_succeeds_for_anthropic_native_tools(self, mock_telemetry):
        """Anthropic native_tools do not require Responses API.

        The v26 validation only applies to OpenAI provider.
        Anthropic native tools should pass through without checking the flag.
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            telemetry=mock_telemetry,
        )

        # Mock feature_flags - Responses API flag is False but shouldn't matter
        with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_feature_flags:
            mock_feature_flags.use_responses_api_for_openai = False  # Disabled

            # Should not raise ValueError - validation only applies to OpenAI
            try:
                await factory.ainvoke(
                    messages=[{"role": "user", "content": "Hello"}],
                    native_tools=[{"name": "computer", "type": "computer_20241022"}],
                )
            except ValueError as e:
                if "use_responses_api_for_openai" in str(e):
                    pytest.fail("Should not raise ValueError for Anthropic")
                raise
            except Exception:
                # Any other exception is fine - validation passed
                pass

    @pytest.mark.asyncio
    async def test_ainvoke_succeeds_for_google_native_tools(self, mock_telemetry):
        """Google native_tools do not require Responses API.

        The v26 validation only applies to OpenAI provider.
        Google native tools should pass through without checking the flag.
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-1.5-pro",
            telemetry=mock_telemetry,
        )

        with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_feature_flags:
            mock_feature_flags.use_responses_api_for_openai = False  # Disabled

            # Should not raise ValueError - validation only applies to OpenAI
            try:
                await factory.ainvoke(
                    messages=[{"role": "user", "content": "Hello"}],
                    native_tools=[{"type": "code_execution"}],
                )
            except ValueError as e:
                if "use_responses_api_for_openai" in str(e):
                    pytest.fail("Should not raise ValueError for Google")
                raise
            except Exception:
                # Any other exception is fine - validation passed
                pass

    @pytest.mark.asyncio
    async def test_astream_raises_valueerror_for_openai_native_tools_without_responses_api(self, mock_telemetry):
        """OpenAI native_tools without Responses API raises ValueError in astream()."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Mock feature_flags to disable Responses API
        with patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_feature_flags:
            mock_feature_flags.use_responses_api_for_openai = False
            mock_feature_flags.enable_llm_hooks = False
            mock_feature_flags.adaptive_concurrency = False
            mock_feature_flags.adaptive_timeout = False
            mock_feature_flags.adaptive_retry = False
            mock_feature_flags.enable_llm_token_counting = False

            with pytest.raises(ValueError, match="use_responses_api_for_openai"):
                async for _ in factory.astream(
                    messages=[{"role": "user", "content": "Hello"}],
                    native_tools=[{"type": "code_interpreter"}],
                ):
                    pass
