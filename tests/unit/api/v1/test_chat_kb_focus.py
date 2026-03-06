"""
Chat Router KB Focus Mode Tests

TDD tests for KB (Knowledge Base) Focus Mode integration.

KB Focus Mode allows users to control context retrieval strategy:
- "all": Use both KB and web search (default)
- "kb_only": Only use KB/vector store for context
- "web_only": Only use web search for context
- "none": Disable context augmentation

Tests written FIRST before implementation (RED phase).
"""

import gc
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.llm.factory import StreamChunk

pytestmark = [pytest.mark.unit, pytest.mark.chat, pytest.mark.kb_focus]


# =============================================================================
# ChatCompletionRequest Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_kb_focus")
class TestChatCompletionRequestKBFocus:
    """Tests for kb_focus field in ChatCompletionRequest model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chat_completion_request_has_kb_focus_field(self) -> None:
        """
        GIVEN the ChatCompletionRequest model
        WHEN checking model fields
        THEN kb_focus should exist as an optional field
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        # Check that kb_focus field exists in model
        assert "kb_focus" in ChatCompletionRequest.model_fields

    def test_chat_completion_request_kb_focus_default_all(self) -> None:
        """
        GIVEN a ChatCompletionRequest without explicit kb_focus
        WHEN creating the request
        THEN kb_focus should default to "all"
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        request = ChatCompletionRequest(
            session_id="test-session",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert request.kb_focus == "all"

    def test_chat_completion_request_kb_focus_accepts_valid_values(self) -> None:
        """
        GIVEN ChatCompletionRequest
        WHEN kb_focus is set to valid values
        THEN request should be created successfully
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        valid_modes: list[Literal["all", "kb_only", "web_only", "none"]] = [
            "all",
            "kb_only",
            "web_only",
            "none",
        ]

        for mode in valid_modes:
            request = ChatCompletionRequest(
                session_id="test-session",
                messages=[{"role": "user", "content": "Hello"}],
                kb_focus=mode,
            )
            assert request.kb_focus == mode

    def test_chat_completion_request_kb_focus_rejects_invalid_values(self) -> None:
        """
        GIVEN ChatCompletionRequest
        WHEN kb_focus is set to an invalid value
        THEN ValidationError should be raised
        """
        from mcp_server_langgraph.api.v1.chat import ChatCompletionRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                session_id="test-session",
                messages=[{"role": "user", "content": "Hello"}],
                kb_focus="invalid_mode",  # type: ignore[arg-type]
            )

        # Check that the error is about kb_focus
        error_str = str(exc_info.value)
        assert "kb_focus" in error_str


# =============================================================================
# Streaming Endpoint KB Focus Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_kb_focus")
class TestStreamingEndpointKBFocus:
    """Tests for kb_focus parameter in streaming endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stream_passes_kb_focus_to_service(self) -> None:
        """
        GIVEN a streaming request with kb_focus="kb_only"
        WHEN create_stream is called
        THEN the service.create_stream should receive kb_focus parameter
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Hello", chunk_index=0, is_final=False)
            yield StreamChunk(content="", chunk_index=1, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        # Spy on the method to capture kwargs
        kb_focus_received = None

        original_create_stream = service.create_stream

        async def spy_create_stream(*args, **kwargs):
            nonlocal kb_focus_received
            kb_focus_received = kwargs.get("kb_focus")
            async for chunk in original_create_stream(*args, **kwargs):
                yield chunk

        service.create_stream = spy_create_stream

        messages = [{"role": "user", "content": "Hi"}]

        # Call with kb_focus
        async for _ in service.create_stream(
            session_id="session-1",
            messages=messages,
            kb_focus="kb_only",
        ):
            pass

        # kb_focus should be captured
        assert kb_focus_received == "kb_only"

    @pytest.mark.asyncio
    async def test_create_stream_accepts_all_kb_focus_modes(self) -> None:
        """
        GIVEN a streaming request with different kb_focus values
        WHEN create_stream is called
        THEN it should accept all valid modes without error

        This test verifies that all kb_focus modes are handled.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Response", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # Test all valid kb_focus modes
        for mode in ["all", "kb_only", "web_only", "none"]:
            chunks = []
            async for chunk in service.create_stream(
                session_id="session-1",
                messages=messages,
                kb_focus=mode,
            ):
                chunks.append(chunk)

            # Should have received at least one chunk
            assert len(chunks) >= 1


# =============================================================================
# ChatServiceImpl KB Focus Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_kb_focus")
class TestChatServiceImplKBFocus:
    """Tests for ChatServiceImpl kb_focus handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_create_stream_accepts_kb_focus_parameter(self) -> None:
        """
        GIVEN ChatServiceImpl.create_stream
        WHEN called with kb_focus parameter
        THEN it should accept the parameter without error
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Test", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # Should not raise TypeError for unexpected keyword argument
        chunks = []
        async for chunk in service.create_stream(
            session_id="session-1",
            messages=messages,
            kb_focus="kb_only",
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_service_kb_focus_parameter_signature(self) -> None:
        """
        GIVEN ChatServiceImpl.create_stream method
        WHEN checking the method signature
        THEN it should accept kb_focus parameter

        This tests that kb_focus is a valid parameter for create_stream.
        """
        import inspect
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Check that create_stream method accepts kb_focus
        sig = inspect.signature(ChatServiceImpl.create_stream)
        param_names = list(sig.parameters.keys())

        # kb_focus should be in the parameter list
        # (could be explicit param or captured via **kwargs)
        assert "kb_focus" in param_names or "kwargs" in param_names


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_kb_focus")
class TestKBFocusFeatureFlag:
    """Tests for kb_focus feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_kb_focus_feature_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_kb_focus
        THEN it should exist as a boolean field
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_kb_focus")
        assert isinstance(flags.enable_kb_focus, bool)

    def test_kb_focus_feature_flag_default_true(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN using default values
        THEN enable_kb_focus should default to True (enabled by default)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        # Default to True - KB focus is a production feature
        assert flags.enable_kb_focus is True

    @pytest.mark.asyncio
    async def test_kb_focus_works_when_flag_enabled(self) -> None:
        """
        GIVEN enable_kb_focus=True (default)
        WHEN create_stream is called with kb_focus parameter
        THEN kb_focus should be processed without error
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Verify the flag is enabled by default
        flags = FeatureFlags()
        assert flags.enable_kb_focus is True

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Test", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # With kb_focus="kb_only", should work without error
        chunks = []
        async for chunk in service.create_stream(
            session_id="session-1",
            messages=messages,
            kb_focus="kb_only",
        ):
            chunks.append(chunk)

        # Should receive response
        assert len(chunks) >= 1


# =============================================================================
# Non-Streaming Endpoint KB Focus Tests
# =============================================================================


class TestNonStreamingEndpointKBFocus:
    """Tests for kb_focus parameter in non-streaming create_completion endpoint.

    TDD: These tests verify that kb_focus is passed to the non-stream path
    (Finding 2.1: kb_focus NOT passed in non-stream create_completion() call).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_completion_passes_kb_focus_to_service(self) -> None:
        """
        GIVEN a non-streaming request with kb_focus="kb_only"
        WHEN create_completion endpoint is called
        THEN the service.create_completion should receive kb_focus parameter
        """
        from langchain_core.messages import AIMessage
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Hello response"))

        service = ChatServiceImpl(llm_factory=mock_factory)

        # Spy on the method to capture kwargs
        kb_focus_received = None
        original_create_completion = service.create_completion

        async def spy_create_completion(*args, **kwargs):
            nonlocal kb_focus_received
            kb_focus_received = kwargs.get("kb_focus")
            return await original_create_completion(*args, **kwargs)

        service.create_completion = spy_create_completion

        messages = [{"role": "user", "content": "Hi"}]

        # Call with kb_focus
        await service.create_completion(
            session_id="session-1",
            messages=messages,
            kb_focus="kb_only",
        )

        # kb_focus should be captured
        assert kb_focus_received == "kb_only"

    @pytest.mark.asyncio
    async def test_create_completion_accepts_all_kb_focus_modes(self) -> None:
        """
        GIVEN a non-streaming request with different kb_focus values
        WHEN create_completion is called
        THEN it should accept all valid modes without error
        """
        from langchain_core.messages import AIMessage
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()
        mock_factory.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # Test all valid kb_focus modes
        for mode in ["all", "kb_only", "web_only", "none"]:
            response = await service.create_completion(
                session_id="session-1",
                messages=messages,
                kb_focus=mode,
            )

            # Should have received a response
            assert response is not None

    @pytest.mark.asyncio
    async def test_service_create_completion_signature_accepts_kb_focus(self) -> None:
        """
        GIVEN ChatServiceImpl.create_completion method
        WHEN checking the method signature
        THEN it should accept kb_focus parameter (either explicit or via **kwargs)
        """
        import inspect
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Check that create_completion method accepts kb_focus
        sig = inspect.signature(ChatServiceImpl.create_completion)
        param_names = list(sig.parameters.keys())

        # kb_focus should be in the parameter list
        # (could be explicit param or captured via **kwargs)
        assert "kb_focus" in param_names or "kwargs" in param_names

    @pytest.mark.asyncio
    async def test_endpoint_passes_kb_focus_from_request_to_service(self) -> None:
        """
        GIVEN a ChatCompletionRequest with kb_focus="kb_only"
        WHEN the create_completion endpoint handler is invoked
        THEN the service.create_completion should receive kb_focus from the request

        This tests the ENDPOINT wiring specifically (Finding 2.1).
        The endpoint at chat.py:1138-1148 must include kb_focus=request.kb_focus.
        """
        from mcp_server_langgraph.api.v1.chat import (
            ChatCompletionRequest,
            ChatMessage,
            create_completion,
        )

        # Create request with kb_focus
        request = ChatCompletionRequest(
            session_id="test-session",
            messages=[ChatMessage(role="user", content="Hello")],
            kb_focus="kb_only",
        )

        # Track what kwargs are passed to service.create_completion
        captured_kwargs = {}

        async def mock_create_completion(session_id, messages, **kwargs):
            captured_kwargs.update(kwargs)
            return {
                "id": "resp-123",
                "message": {"role": "assistant", "content": "Hi"},
                "model": "test-model",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

        mock_service = MagicMock()
        mock_service.create_completion = mock_create_completion

        # Mock current_user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.chat.get_chat_service", return_value=mock_service):
            # Call the endpoint handler - result unused, we verify via captured_kwargs
            await create_completion(request, mock_user)

        # Verify kb_focus was passed to the service
        assert "kb_focus" in captured_kwargs, "kb_focus not passed from endpoint to service"
        assert captured_kwargs["kb_focus"] == "kb_only"
