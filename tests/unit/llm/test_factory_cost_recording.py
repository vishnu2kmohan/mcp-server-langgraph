"""
TDD RED Phase: Tests for LLM Factory PostgreSQL cost recording.

These tests verify that:
1. LLM factory records costs to PostgreSQL via CostMetricsCollector
2. Cost recording happens for both acompletion and responses API paths
3. Cost recording includes required fields (user_id, session_id, model, etc.)
4. Cost recording is async and non-blocking
5. Cost recording failure doesn't fail the LLM call

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.llm.factory import LLMFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_acompletion_response():
    """Create a mock acompletion response with usage data."""
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150

    mock_message = MagicMock()
    mock_message.content = "Test response"

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    return mock_response


@pytest.fixture
def mock_cost_metrics_collector():
    """Create a mock CostMetricsCollector."""
    mock_collector = AsyncMock(return_value=None)
    mock_collector.record_usage = AsyncMock(return_value=None)
    return mock_collector


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="llm_factory_cost")
class TestLLMFactoryCostRecording:
    """
    TDD tests for LLM Factory PostgreSQL cost recording.

    These tests verify that costs are recorded to PostgreSQL
    via CostMetricsCollector.record_usage() in addition to
    Prometheus metrics.
    """

    def setup_method(self):
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )

        reset_singleton_dependencies()
        reset_cost_storage_backend()

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        gc.collect()

    async def test_ainvoke_records_cost_to_postgres(
        self,
        mock_acompletion_response,
    ):
        """
        RED: Verify ainvoke() calls CostMetricsCollector.record_usage().

        This test validates that the LLM factory records cost data to
        PostgreSQL after each successful LLM invocation.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            # Call ainvoke
            await factory.ainvoke(
                messages=[{"role": "user", "content": "Hello"}],
                user_id="test-user",
                session_id="test-session",
            )

            # Verify CostMetricsCollector.record_usage was called
            mock_collector.record_usage.assert_called_once()

            # Verify the call had required fields
            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["provider"] == "openai"
            assert call_kwargs["prompt_tokens"] == 100
            assert call_kwargs["completion_tokens"] == 50
            assert call_kwargs["user_id"] == "test-user"
            assert call_kwargs["session_id"] == "test-session"

    async def test_ainvoke_records_cost_with_correct_tokens(
        self,
        mock_acompletion_response,
    ):
        """
        RED: Verify token counts are correctly passed to cost recording.
        """
        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            api_key="test-key",
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            # Custom token counts
            mock_acompletion_response.usage.prompt_tokens = 500
            mock_acompletion_response.usage.completion_tokens = 250
            mock_acompletion.return_value = mock_acompletion_response

            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Test"}],
                user_id="user-123",
                session_id="session-456",
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["prompt_tokens"] == 500
            assert call_kwargs["completion_tokens"] == 250

    async def test_cost_recording_failure_does_not_fail_llm_call(
        self,
        mock_acompletion_response,
    ):
        """
        RED: Verify LLM call succeeds even if cost recording fails.

        Cost recording should be non-blocking. If it fails, the LLM
        response should still be returned to the caller.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response

            # Make cost recording fail
            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(side_effect=Exception("Database error"))
            mock_get_collector.return_value = mock_collector
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            # Call should still succeed
            result = await factory.ainvoke(
                messages=[{"role": "user", "content": "Hello"}],
                user_id="test-user",
                session_id="test-session",
            )

            # Response should still be returned
            assert result.content == "Test response"

    async def test_cost_recording_skipped_when_disabled(
        self,
        mock_acompletion_response,
    ):
        """
        RED: Verify cost recording is skipped when feature flag is disabled.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            # Disable cost tracking
            mock_flags.enable_cost_tracking = False
            mock_flags.enable_llm_hooks = False

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Hello"}],
                user_id="test-user",
                session_id="test-session",
            )

            # record_usage should NOT be called
            mock_collector.record_usage.assert_not_called()

    async def test_cost_recording_includes_timestamp(
        self,
        mock_acompletion_response,
    ):
        """
        RED: Verify cost recording includes a timestamp.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            mock_acompletion.return_value = mock_acompletion_response
            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Hello"}],
                user_id="test-user",
                session_id="test-session",
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert "timestamp" in call_kwargs
            assert isinstance(call_kwargs["timestamp"], datetime)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="llm_factory_cost")
class TestLLMFactoryCostRecordingResponsesAPI:
    """
    TDD tests for cost recording via OpenAI Responses API path.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )

        reset_singleton_dependencies()
        reset_cost_storage_backend()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.monitoring.cost_storage_factory import (
            reset_cost_storage_backend,
        )

        reset_singleton_dependencies()
        reset_cost_storage_backend()
        gc.collect()

    async def test_responses_api_records_cost_to_postgres(self):
        """
        RED: Verify Responses API path also records costs.

        When using OpenAI native tools via Responses API, costs
        should still be recorded to PostgreSQL.
        """
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
        )

        mock_responses_output = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Search results..."}],
                }
            ],
            "usage": {
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
            },
        }

        with (
            patch.object(factory, "_call_responses_api", new_callable=AsyncMock) as mock_responses,
            patch("mcp_server_langgraph.llm.factory.get_cost_collector") as mock_get_collector,
            patch("mcp_server_langgraph.llm.factory.feature_flags") as mock_flags,
        ):
            from types import SimpleNamespace

            mock_responses.return_value = (
                "Search results...",
                SimpleNamespace(prompt_tokens=200, completion_tokens=100, total_tokens=300),
                mock_responses_output["output"],
            )

            mock_collector = AsyncMock(return_value=None)
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_llm_hooks = False
            mock_flags.use_responses_api_for_openai = True

            await factory.ainvoke(
                messages=[{"role": "user", "content": "Search for AI news"}],
                user_id="test-user",
                session_id="test-session",
                native_tools=[{"type": "web_search_preview"}],
            )

            # Verify cost recording was called
            mock_collector.record_usage.assert_called_once()

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["prompt_tokens"] == 200
            assert call_kwargs["completion_tokens"] == 100
