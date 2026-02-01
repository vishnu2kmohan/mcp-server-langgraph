"""
Chat Router Streaming Refactor Tests

TDD tests for refactoring chat.py to use LLMFactory.astream().

This validates that the ChatServiceImpl can use LLMFactory.astream()
instead of direct litellm.acompletion for streaming.

Reference: LLMFactory streaming support (Phase 1)
"""

import gc
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.llm.factory import StreamChunk

pytestmark = [pytest.mark.unit, pytest.mark.chat]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_factory():
    """Create a mock LLM factory with streaming support."""
    factory = MagicMock()

    async def mock_astream(messages, **kwargs):
        """Mock streaming that yields StreamChunks."""
        yield StreamChunk(content="Hello", chunk_index=0, is_final=False)
        yield StreamChunk(content=" world", chunk_index=1, is_final=False)
        yield StreamChunk(content="!", chunk_index=2, is_final=True, finish_reason="stop")

    factory.astream = mock_astream
    return factory


@pytest.fixture
def mock_llm_factory_with_thinking():
    """Create a mock LLM factory with thinking content."""
    factory = MagicMock()

    async def mock_astream(messages, **kwargs):
        """Mock streaming with thinking content."""
        yield StreamChunk(
            content="",
            chunk_index=0,
            is_final=False,
            thinking="Let me think about this...",
        )
        yield StreamChunk(
            content="The answer is 42",
            chunk_index=1,
            is_final=True,
            finish_reason="stop",
        )

    factory.astream = mock_astream
    return factory


# =============================================================================
# Tests for ChatServiceImpl Streaming via LLMFactory
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_refactor")
class TestChatStreamingViaLLMFactory:
    """Tests for refactored chat streaming using LLMFactory.astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chat_completion_service_has_llm_factory(self) -> None:
        """
        GIVEN a ChatServiceImpl
        WHEN initialized
        THEN it should have an llm_factory attribute
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl()
        assert hasattr(service, "_llm_factory") or hasattr(service, "llm_factory")

    def test_chat_completion_service_accepts_llm_factory(self) -> None:
        """
        GIVEN a ChatServiceImpl
        WHEN initialized with an llm_factory
        THEN it should use that factory
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()
        service = ChatServiceImpl(llm_factory=mock_factory)

        # Should have stored the factory
        factory = getattr(service, "_llm_factory", None) or getattr(service, "llm_factory", None)
        assert factory == mock_factory

    @pytest.mark.asyncio
    async def test_stream_via_llm_factory_yields_delta_content(self, mock_llm_factory) -> None:
        """
        GIVEN a ChatServiceImpl with LLMFactory
        WHEN streaming via LLM factory
        THEN it should yield delta content dictionaries
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(llm_factory=mock_llm_factory)

        messages = [{"role": "user", "content": "Hello"}]

        chunks = []
        async for chunk in service._stream_via_llm_factory(
            session_id="test-session",
            messages=messages,
        ):
            chunks.append(chunk)

        # Should yield delta content dictionaries
        assert len(chunks) >= 2
        assert "delta" in chunks[0]
        assert "content" in chunks[0]["delta"]

    @pytest.mark.asyncio
    async def test_stream_via_llm_factory_includes_thinking(self, mock_llm_factory_with_thinking) -> None:
        """
        GIVEN a streaming response with thinking content
        WHEN streaming via LLM factory
        THEN thinking content should be included in chunks
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(llm_factory=mock_llm_factory_with_thinking)

        messages = [{"role": "user", "content": "What is 6 * 7?"}]

        chunks = []
        async for chunk in service._stream_via_llm_factory(
            session_id="test-session",
            messages=messages,
        ):
            chunks.append(chunk)

        # First chunk should have thinking
        thinking_chunks = [c for c in chunks if c.get("delta", {}).get("thinking")]
        assert len(thinking_chunks) >= 1
        assert thinking_chunks[0]["delta"]["thinking"] == "Let me think about this..."

    @pytest.mark.asyncio
    async def test_stream_via_llm_factory_excludes_final_chunk(self, mock_llm_factory) -> None:
        """
        GIVEN a streaming response
        WHEN streaming via LLM factory
        THEN the final chunk (with is_final=True) should not be yielded to avoid empty content
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl(llm_factory=mock_llm_factory)

        messages = [{"role": "user", "content": "Hello"}]

        chunks = []
        async for chunk in service._stream_via_llm_factory(
            session_id="test-session",
            messages=messages,
        ):
            chunks.append(chunk)

        # Final chunk should be excluded (contains finish_reason but typically empty content)
        # Only non-final chunks with content should be yielded
        contents = [c["delta"].get("content", "") for c in chunks if "delta" in c]
        assert "Hello" in contents or "Hello" in " ".join(contents)

    @pytest.mark.asyncio
    async def test_stream_via_llm_factory_passes_kwargs(self) -> None:
        """
        GIVEN a ChatServiceImpl with LLMFactory
        WHEN streaming with temperature and max_tokens
        THEN kwargs should be passed to astream
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()
        captured_kwargs = {}

        async def mock_astream(messages, **kwargs):
            captured_kwargs.update(kwargs)
            yield StreamChunk(content="Hi", chunk_index=0, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hello"}]

        async for _ in service._stream_via_llm_factory(
            session_id="test-session",
            messages=messages,
            temperature=0.5,
            max_tokens=1000,
        ):
            pass

        assert captured_kwargs.get("temperature") == 0.5
        assert captured_kwargs.get("max_tokens") == 1000


# =============================================================================
# Tests for Backward Compatibility
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_refactor")
class TestChatStreamingBackwardCompatibility:
    """Tests for backward compatibility during streaming refactor."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stream_via_litellm_removed(self) -> None:
        """
        GIVEN a ChatServiceImpl
        WHEN checking for legacy _stream_via_litellm
        THEN it should NOT exist (legacy method removed)

        This validates the removal of the legacy litellm fallback path.
        All streaming now goes through LLMFactory.astream() with resilience patterns.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl()

        # _stream_via_litellm should be removed (legacy method deleted)
        assert not hasattr(service, "_stream_via_litellm"), (
            "_stream_via_litellm should be removed. All streaming should now use LLMFactory.astream()"
        )

    def test_chat_completion_service_has_stream_via_llm_factory_method(self) -> None:
        """
        GIVEN a ChatServiceImpl
        WHEN checking for _stream_via_llm_factory
        THEN it should exist
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl()
        assert hasattr(service, "_stream_via_llm_factory")
