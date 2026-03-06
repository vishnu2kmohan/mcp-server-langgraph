"""
Chat Cost Tracking Tests

TDD tests for cost tracking integration in the chat API.

With the callback-based architecture (CostTrackingCallback in llm/factory.py),
cost tracking is handled automatically by LiteLLM. These tests verify that:
1. Metadata is correctly passed to acompletion (which the callback extracts)
2. The completion works correctly regardless of cost tracking

The callback behavior itself is tested in test_litellm_cost_callback.py.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.api
class TestChatCostTracking:
    """Tests for cost tracking metadata in chat completions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_litellm_completion_returns_response(self) -> None:
        """Verify that LiteLLM completion returns the expected response."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                user_id="user-456",
            )

            # Verify completion succeeded
            assert result["message"]["content"] == "Hello, I'm here to help!"

            # Verify metadata was passed to acompletion for callback
            call_kwargs = mock_acompletion.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("session_id") == "session-123"
            assert metadata.get("user_id") == "user-456"
            assert metadata.get("feature") == "chat"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_model_to_acompletion(self) -> None:
        """Verify that model is correctly passed to acompletion."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                model="claude-3-opus",
            )

            # Verify model was passed to acompletion
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["model"] == "claude-3-opus"

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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            # Should still return response even without usage data
            assert result["message"]["content"] == "Response"

    @pytest.mark.asyncio
    async def test_litellm_completion_uses_chat_feature_tag(self) -> None:
        """Verify that metadata includes 'chat' feature tag for cost attribution."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            call_kwargs = mock_acompletion.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("feature") == "chat"

    @pytest.mark.asyncio
    async def test_litellm_completion_returns_trace_id_in_response(self) -> None:
        """Verify that trace_id from OpenTelemetry context is returned in response."""
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
            patch.object(service, "_get_current_trace_id", return_value="trace-abc123def456"),
        ):
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            result = await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
            )

            # Verify trace_id is returned in the response (computed after completion)
            assert result.get("trace_id") == "trace-abc123def456"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_workflow_id_in_metadata(self) -> None:
        """Verify that workflow_id is passed in metadata for cost attribution."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                workflow_id="workflow-xyz-789",
            )

            call_kwargs = mock_acompletion.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("workflow_id") == "workflow-xyz-789"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_orchestrator_id_in_metadata(self) -> None:
        """Verify that orchestrator_id is passed in metadata for cost attribution."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                orchestrator_id="orchestrator-main-001",
            )

            call_kwargs = mock_acompletion.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("orchestrator_id") == "orchestrator-main-001"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_organization_id_in_metadata(self) -> None:
        """Verify that organization_id is passed in OTEL metadata for callback."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                organization_id="organization:acme-corp",
            )

            # Verify organization_id is passed to LiteLLM via metadata
            acompletion_call_kwargs = mock_acompletion.call_args.kwargs
            metadata = acompletion_call_kwargs.get("metadata", {})
            assert metadata.get("organization_id") == "organization:acme-corp"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_project_id_in_metadata(self) -> None:
        """Verify that project_id is passed in OTEL metadata for callback."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                project_id="project:backend-api",
            )

            # Verify project_id is passed to LiteLLM via metadata
            acompletion_call_kwargs = mock_acompletion.call_args.kwargs
            metadata = acompletion_call_kwargs.get("metadata", {})
            assert metadata.get("project_id") == "project:backend-api"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_team_id_in_metadata(self) -> None:
        """Verify that team_id is passed in OTEL metadata for callback."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                team_id="team:platform-engineering",
            )

            # Verify team_id is passed to LiteLLM via metadata
            acompletion_call_kwargs = mock_acompletion.call_args.kwargs
            metadata = acompletion_call_kwargs.get("metadata", {})
            assert metadata.get("team_id") == "team:platform-engineering"

    @pytest.mark.asyncio
    async def test_litellm_completion_passes_full_org_hierarchy_in_metadata(self) -> None:
        """Verify that full organizational hierarchy is passed in metadata."""
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

        with patch("mcp_server_langgraph.api.v1.chat.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            messages = [{"role": "user", "content": "Hello"}]
            await service._create_completion_via_litellm(
                session_id="session-123",
                messages=messages,
                user_id="user:alice",
                organization_id="organization:acme-corp",
                project_id="project:backend-api",
                team_id="team:platform-engineering",
            )

            # Verify full hierarchy in OTEL metadata
            acompletion_call_kwargs = mock_acompletion.call_args.kwargs
            metadata = acompletion_call_kwargs.get("metadata", {})
            assert metadata.get("user_id") == "user:alice"
            assert metadata.get("organization_id") == "organization:acme-corp"
            assert metadata.get("project_id") == "project:backend-api"
            assert metadata.get("team_id") == "team:platform-engineering"
            assert metadata.get("session_id") == "session-123"
            assert metadata.get("feature") == "chat"
