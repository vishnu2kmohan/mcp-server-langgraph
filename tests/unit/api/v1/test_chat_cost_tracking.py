"""
Chat Cost Tracking Tests

TDD tests for cost tracking integration in the chat API.

This ensures that LLM token usage is recorded to the CostMetricsCollector
so that the /api/v1/cost endpoints and /studio/cost page display accurate data.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_chat_cost_tracking")
@pytest.mark.unit
@pytest.mark.api
class TestChatCostTracking:
    """Tests for cost tracking in chat completions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_litellm_completion_records_cost(self) -> None:
        """Verify that LiteLLM completion records usage to cost collector."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock response with usage
        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Hello, I'm here to help!"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                user_id="user-456",
            )

            # Verify completion succeeded
            assert result["message"]["content"] == "Hello, I'm here to help!"

            # Verify cost was recorded
            mock_collector.record_usage.assert_called_once()
            call_kwargs = mock_collector.record_usage.call_args.kwargs

            assert call_kwargs["session_id"] == "session-123"
            assert call_kwargs["user_id"] == "user-456"
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["prompt_tokens"] == 100
            assert call_kwargs["completion_tokens"] == 50

    @pytest.mark.asyncio
    async def test_litellm_completion_infers_provider(self) -> None:
        """Verify that provider is correctly inferred from model name."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "claude-3-opus"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                model="claude-3-opus",
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_litellm_completion_handles_no_usage(self) -> None:
        """Verify graceful handling when response has no usage data."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = None  # No usage data
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            # Should still return response
            assert result["message"]["content"] == "Response"

            # Should NOT call record_usage when there's no usage data
            mock_collector.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_litellm_completion_uses_chat_feature_tag(self) -> None:
        """Verify that cost records are tagged with 'chat' feature."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_cost_tracking_error_does_not_fail_completion(self) -> None:
        """Verify that cost tracking errors don't break the completion."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            # Make record_usage raise an exception
            mock_collector.record_usage = AsyncMock(side_effect=Exception("Database error"))
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            # Should NOT raise - cost tracking errors are caught
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            # Should still return response
            assert result["message"]["content"] == "Response"

    @pytest.mark.asyncio
    async def test_litellm_completion_captures_trace_id(self) -> None:
        """Verify that trace_id from OpenTelemetry context is passed to cost collector."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
            patch.object(service, "_get_current_trace_id", return_value="trace-abc123def456"),
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs.get("trace_id") == "trace-abc123def456"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_workflow_id(self) -> None:
        """Verify that workflow_id from kwargs is passed to cost collector."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                workflow_id="workflow-xyz-789",
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs.get("workflow_id") == "workflow-xyz-789"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_orchestrator_id(self) -> None:
        """Verify that orchestrator_id from kwargs is passed to cost collector."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-test123"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.content = "Response"

        service = ChatServiceImpl()

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.get_cost_collector") as mock_get_collector,
        ):
            mock_acompletion.return_value = mock_response

            mock_collector = MagicMock()
            mock_collector.record_usage = AsyncMock(return_value=None)
            mock_get_collector.return_value = mock_collector

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                orchestrator_id="orchestrator-main-001",
            )

            call_kwargs = mock_collector.record_usage.call_args.kwargs
            assert call_kwargs.get("orchestrator_id") == "orchestrator-main-001"
