"""
Tests for MCP Sampling Protocol (2025-06-18 Spec).

Tests the sampling/createMessage endpoint that allows servers to request
LLM completions from clients. Enables agentic behaviors with nested LLM calls.
"""

import gc
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.mcp.sampling import (
    ModelHint,
    ModelPreferences,
    SamplingHandler,
    SamplingMessage,
    SamplingMessageContent,
    SamplingRequest,
    SamplingResponse,
)

# Module-level marker for test categorization
pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="mcp_sampling")
@pytest.mark.unit
class TestSamplingModels:
    """Test sampling data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sampling_message_text_content(self) -> None:
        """Test text message content."""
        content = SamplingMessageContent(type="text", text="Hello, world!")
        assert content.type == "text"
        assert content.text == "Hello, world!"

    def test_sampling_message_image_content(self) -> None:
        """Test image message content with base64 data."""
        content = SamplingMessageContent(
            type="image",
            data="base64encodeddata",
            mimeType="image/png",
        )
        assert content.type == "image"
        assert content.data == "base64encodeddata"
        assert content.mimeType == "image/png"

    def test_sampling_message_user_role(self) -> None:
        """Test user message."""
        message = SamplingMessage(
            role="user",
            content=SamplingMessageContent(type="text", text="What is 2+2?"),
        )
        assert message.role == "user"
        assert message.content.text == "What is 2+2?"

    def test_sampling_message_assistant_role(self) -> None:
        """Test assistant message."""
        message = SamplingMessage(
            role="assistant",
            content=SamplingMessageContent(type="text", text="2+2 equals 4."),
        )
        assert message.role == "assistant"

    def test_model_hint_creation(self) -> None:
        """Test model hint with substring matching."""
        hint = ModelHint(name="claude-3-sonnet")
        assert hint.name == "claude-3-sonnet"

    def test_model_preferences_priorities(self) -> None:
        """Test model preferences with priority scales."""
        prefs = ModelPreferences(
            hints=[ModelHint(name="claude-3-sonnet"), ModelHint(name="claude")],
            costPriority=0.3,
            speedPriority=0.8,
            intelligencePriority=0.5,
        )
        assert len(prefs.hints) == 2
        assert prefs.costPriority == 0.3
        assert prefs.speedPriority == 0.8
        assert prefs.intelligencePriority == 0.5

    def test_model_preferences_defaults(self) -> None:
        """Test default model preferences."""
        prefs = ModelPreferences()
        assert prefs.hints == []
        assert prefs.costPriority is None
        assert prefs.speedPriority is None
        assert prefs.intelligencePriority is None

    def test_sampling_request_creation(self) -> None:
        """Test full sampling request."""
        request = SamplingRequest(
            id=str(uuid.uuid4()),
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Summarize this"),
                )
            ],
            modelPreferences=ModelPreferences(
                hints=[ModelHint(name="claude-3-sonnet")],
                intelligencePriority=0.8,
            ),
            systemPrompt="You are a helpful assistant.",
            maxTokens=500,
        )
        assert len(request.messages) == 1
        assert request.systemPrompt == "You are a helpful assistant."
        assert request.maxTokens == 500

    def test_sampling_response_creation(self) -> None:
        """Test sampling response with model info."""
        response = SamplingResponse(
            role="assistant",
            content=SamplingMessageContent(
                type="text",
                text="This code implements a sorting algorithm...",
            ),
            model="claude-3-sonnet-20240307",
            stopReason="endTurn",
        )
        assert response.role == "assistant"
        assert response.model == "claude-3-sonnet-20240307"
        assert response.stopReason == "endTurn"


@pytest.mark.xdist_group(name="mcp_sampling")
@pytest.mark.unit
class TestSamplingHandler:
    """Test SamplingHandler for managing sampling requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> SamplingHandler:
        """Create a fresh sampling handler."""
        return SamplingHandler()

    def test_create_sampling_request(self, handler: SamplingHandler) -> None:
        """Test creating a new sampling request."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Analyze this"),
                )
            ],
            system_prompt="You are a code analyst.",
            max_tokens=1000,
        )
        assert request.id is not None
        assert request.status == "pending"
        assert request.maxTokens == 1000

    def test_create_request_with_preferences(self, handler: SamplingHandler) -> None:
        """Test creating request with model preferences."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
            model_preferences=ModelPreferences(
                hints=[ModelHint(name="claude-3-opus")],
                intelligencePriority=1.0,
            ),
        )
        assert len(request.modelPreferences.hints) == 1
        assert request.modelPreferences.intelligencePriority == 1.0

    def test_get_pending_request(self, handler: SamplingHandler) -> None:
        """Test retrieving pending sampling request."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
        )
        pending = handler.get_pending_request(request.id)
        assert pending is not None
        assert pending.id == request.id

    def test_approve_request_updates_status_to_approved(self, handler: SamplingHandler) -> None:
        """Test approving a sampling request."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
        )

        approved = handler.approve_request(request.id)
        assert approved.status == "approved"

    def test_reject_request_stores_reason_and_moves_to_completed(self, handler: SamplingHandler) -> None:
        """Test rejecting a sampling request."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
        )

        rejected = handler.reject_request(request.id, reason="Rate limited")
        assert rejected.status == "rejected"
        assert rejected.rejection_reason == "Rate limited"

    def test_complete_request_with_response_removes_from_pending(self, handler: SamplingHandler) -> None:
        """Test completing a sampling request with response."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Summarize"),
                )
            ],
        )
        handler.approve_request(request.id)

        response = SamplingResponse(
            role="assistant",
            content=SamplingMessageContent(
                type="text",
                text="Here is the summary...",
            ),
            model="claude-3-sonnet-20240307",
            stopReason="endTurn",
        )

        completed = handler.complete_request(request.id, response)
        assert completed.status == "completed"
        assert completed.response is not None
        assert handler.get_pending_request(request.id) is None

    def test_reject_nonexistent_request(self, handler: SamplingHandler) -> None:
        """Test error when rejecting nonexistent request."""
        with pytest.raises(ValueError, match="not found"):
            handler.reject_request("nonexistent-id")

    def test_list_pending_requests(self, handler: SamplingHandler) -> None:
        """Test listing all pending requests."""
        handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="First"),
                )
            ],
        )
        handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Second"),
                )
            ],
        )

        pending = handler.list_pending()
        assert len(pending) == 2

    def test_edit_request_messages(self, handler: SamplingHandler) -> None:
        """Test editing request messages before approval."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Original"),
                )
            ],
        )

        edited = handler.edit_request(
            request.id,
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Edited"),
                )
            ],
        )

        assert edited.messages[0].content.text == "Edited"

    def test_edit_request_system_prompt(self, handler: SamplingHandler) -> None:
        """Test editing system prompt before approval."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
            system_prompt="Original prompt",
        )

        edited = handler.edit_request(
            request.id,
            system_prompt="Edited prompt",
        )

        assert edited.systemPrompt == "Edited prompt"


@pytest.mark.xdist_group(name="mcp_sampling")
@pytest.mark.integration
class TestSamplingJSONRPC:
    """Test sampling via JSON-RPC 2.0 protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> SamplingHandler:
        """Create handler for JSON-RPC tests."""
        return SamplingHandler()

    def test_sampling_request_jsonrpc_format(self, handler: SamplingHandler) -> None:
        """Test sampling/createMessage request in JSON-RPC format."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Summarize this code"),
                )
            ],
            model_preferences=ModelPreferences(
                hints=[ModelHint(name="claude-3-sonnet")],
                intelligencePriority=0.8,
            ),
            system_prompt="You are a code analyst.",
            max_tokens=500,
        )

        jsonrpc_request = request.to_jsonrpc()
        assert jsonrpc_request["jsonrpc"] == "2.0"
        assert jsonrpc_request["method"] == "sampling/createMessage"
        assert "params" in jsonrpc_request
        assert len(jsonrpc_request["params"]["messages"]) == 1
        assert jsonrpc_request["params"]["maxTokens"] == 500

    def test_sampling_response_jsonrpc_format(self, handler: SamplingHandler) -> None:
        """Test sampling response in JSON-RPC format."""
        request = handler.create_request(
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
        )
        handler.approve_request(request.id)

        response = SamplingResponse(
            role="assistant",
            content=SamplingMessageContent(
                type="text",
                text="Response text",
            ),
            model="claude-3-sonnet-20240307",
            stopReason="endTurn",
        )

        jsonrpc_response = response.to_jsonrpc(request.request_id)
        assert jsonrpc_response["jsonrpc"] == "2.0"
        assert jsonrpc_response["id"] == request.request_id
        assert jsonrpc_response["result"]["role"] == "assistant"
        assert jsonrpc_response["result"]["model"] == "claude-3-sonnet-20240307"


@pytest.mark.xdist_group(name="mcp_sampling")
@pytest.mark.integration
class TestSamplingWithLLM:
    """Test integration between Sampling and LLM providers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        """Create mock LLM provider."""
        llm = AsyncMock()
        llm.agenerate.return_value = MagicMock(generations=[[MagicMock(text="Generated response")]])
        # Set model_name as a string to avoid Pydantic validation error
        llm.model_name = "mock-model-v1"
        return llm

    @pytest.mark.asyncio
    async def test_execute_sampling_with_llm(self, mock_llm: AsyncMock) -> None:
        """Test executing sampling request with LLM."""
        from mcp_server_langgraph.mcp.sampling import execute_sampling_request

        request = SamplingRequest(
            id=str(uuid.uuid4()),
            request_id=1,
            messages=[
                SamplingMessage(
                    role="user",
                    content=SamplingMessageContent(type="text", text="Test"),
                )
            ],
            maxTokens=100,
            status="approved",
        )

        response = await execute_sampling_request(request, mock_llm)

        assert response.role == "assistant"
        assert response.content.type == "text"
        mock_llm.agenerate.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_selection_from_hints(self) -> None:
        """Test model selection based on hints."""
        from mcp_server_langgraph.mcp.sampling import select_model_from_preferences

        prefs = ModelPreferences(
            hints=[
                ModelHint(name="claude-3-opus"),
                ModelHint(name="claude-3-sonnet"),
            ],
            intelligencePriority=1.0,
        )

        # Should match first available hint
        selected = select_model_from_preferences(
            prefs,
            available_models=["gpt-4", "claude-3-sonnet-20240307", "claude-3-haiku"],
        )

        # Should match claude-3-sonnet as substring
        assert "sonnet" in selected.lower()

    @pytest.mark.asyncio
    async def test_rate_limiting(self) -> None:
        """Test rate limiting for sampling requests."""
        from mcp_server_langgraph.mcp.sampling import SamplingRateLimiter

        limiter = SamplingRateLimiter(max_requests_per_minute=2)

        # First two should succeed
        assert limiter.allow_request("server-1")
        assert limiter.allow_request("server-1")

        # Third should be rate limited
        assert not limiter.allow_request("server-1")

        # Different server should have separate limit
        assert limiter.allow_request("server-2")
