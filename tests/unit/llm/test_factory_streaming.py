"""
LLM Factory Streaming Support Tests

TDD tests for LLMFactory.astream() - streaming LLM responses.

Phase 1: Minimal viable streaming
- Stream chunks with content
- First-chunk timeout
- Circuit breaker integration (connection failures only)
- Bulkhead slot held for stream duration

Phase 2: Streaming-aware resilience (future)
- Pre-first-chunk retry
- Inter-chunk timeout
- Token counting at stream end

Reference: Analysis from ADR-0026 Cost Tracking Enhancements discussion.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

pytestmark = [pytest.mark.unit, pytest.mark.llm]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings for LLM factory."""
    settings = MagicMock()
    settings.llm_provider = "google"
    settings.model_name = "gemini-2.5-flash"
    settings.model_temperature = 0.7
    settings.model_max_tokens = 4096
    settings.model_timeout = 60
    settings.enable_fallback = False
    settings.fallback_models = []
    settings.google_api_key = "test-api-key"
    settings.vertex_location = "us-central1"
    settings.vertex_project = None
    return settings


@pytest.fixture
def mock_stream_response():
    """Create a mock streaming response."""

    async def stream_generator():
        """Generate mock stream chunks."""

        class MockDelta:
            def __init__(self, content: str, reasoning_content: str | None = None):
                self.content = content
                self.reasoning_content = reasoning_content

        class MockChoice:
            def __init__(self, delta: MockDelta, finish_reason: str | None = None):
                self.delta = delta
                self.finish_reason = finish_reason

        class MockChunk:
            def __init__(self, choices: list[MockChoice]):
                self.choices = choices

        # Yield 3 chunks
        yield MockChunk([MockChoice(MockDelta("Hello"))])
        yield MockChunk([MockChoice(MockDelta(" world"))])
        yield MockChunk([MockChoice(MockDelta("!"), finish_reason="stop")])

    return stream_generator()


# =============================================================================
# Phase 1: StreamChunk Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="llm_streaming")
class TestStreamChunkModel:
    """Tests for the StreamChunk data model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_stream_chunk_model_exists(self) -> None:
        """
        GIVEN the llm.factory module
        WHEN importing StreamChunk
        THEN it should be available
        """
        from mcp_server_langgraph.llm.factory import StreamChunk

        assert StreamChunk is not None

    def test_stream_chunk_has_required_fields(self) -> None:
        """
        GIVEN a StreamChunk instance
        WHEN created with required parameters
        THEN it should have all required fields
        """
        from mcp_server_langgraph.llm.factory import StreamChunk

        chunk = StreamChunk(
            content="Hello",
            chunk_index=0,
            is_final=False,
        )

        assert chunk.content == "Hello"
        assert chunk.chunk_index == 0
        assert chunk.is_final is False

    def test_stream_chunk_has_optional_fields(self) -> None:
        """
        GIVEN a StreamChunk instance
        WHEN created with optional parameters
        THEN it should have all optional fields
        """
        from mcp_server_langgraph.llm.factory import StreamChunk

        chunk = StreamChunk(
            content="Thinking...",
            chunk_index=0,
            is_final=False,
            thinking="Let me analyze this...",
            finish_reason=None,
        )

        assert chunk.thinking == "Let me analyze this..."
        assert chunk.finish_reason is None

    def test_stream_chunk_final_with_finish_reason(self) -> None:
        """
        GIVEN a final StreamChunk
        WHEN is_final=True
        THEN it should include finish_reason
        """
        from mcp_server_langgraph.llm.factory import StreamChunk

        chunk = StreamChunk(
            content="Done!",
            chunk_index=5,
            is_final=True,
            finish_reason="stop",
        )

        assert chunk.is_final is True
        assert chunk.finish_reason == "stop"


# =============================================================================
# Phase 1: LLMFactory.astream() Tests
# =============================================================================


@pytest.mark.xdist_group(name="llm_streaming")
class TestLLMFactoryAstream:
    """Tests for LLMFactory.astream() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_astream_method_exists(self) -> None:
        """
        GIVEN the LLMFactory class
        WHEN checking for astream method
        THEN it should exist
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        assert hasattr(LLMFactory, "astream")

    @pytest.mark.asyncio
    async def test_astream_returns_async_iterator(self, mock_settings) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN calling astream()
        THEN it should return an AsyncIterator
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            # Create async iterator for mock
            async def mock_stream():
                class MockDelta:
                    content = "Hello"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            result = factory.astream(messages)

            # Should be an async iterator
            assert hasattr(result, "__aiter__")

    @pytest.mark.asyncio
    async def test_astream_yields_stream_chunks(self, mock_settings) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN iterating over astream() result
        THEN it should yield StreamChunk objects
        """
        from mcp_server_langgraph.llm.factory import LLMFactory, StreamChunk

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    def __init__(self, content):
                        self.content = content
                        self.reasoning_content = None

                class MockChoice:
                    def __init__(self, content, finish_reason=None):
                        self.delta = MockDelta(content)
                        self.finish_reason = finish_reason

                class MockChunk:
                    def __init__(self, content, finish_reason=None):
                        self.choices = [MockChoice(content, finish_reason)]

                yield MockChunk("Hello")
                yield MockChunk(" world")
                yield MockChunk("!", "stop")

            mock_acompletion.return_value = mock_stream()

            chunks = []
            async for chunk in factory.astream(messages):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert all(isinstance(c, StreamChunk) for c in chunks)
            assert chunks[0].content == "Hello"
            assert chunks[1].content == " world"
            assert chunks[2].content == "!"
            assert chunks[2].is_final is True

    @pytest.mark.asyncio
    async def test_astream_includes_thinking_content(self, mock_settings) -> None:
        """
        GIVEN a streaming response with thinking content
        WHEN iterating over astream() result
        THEN chunks should include thinking field
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Think about this")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    def __init__(self, content, reasoning=None):
                        self.content = content
                        self.reasoning_content = reasoning

                class MockChoice:
                    def __init__(self, content, reasoning=None, finish_reason=None):
                        self.delta = MockDelta(content, reasoning)
                        self.finish_reason = finish_reason

                class MockChunk:
                    def __init__(self, content, reasoning=None, finish_reason=None):
                        self.choices = [MockChoice(content, reasoning, finish_reason)]

                yield MockChunk("", "Analyzing the problem...")
                yield MockChunk("The answer is 42", None, "stop")

            mock_acompletion.return_value = mock_stream()

            chunks = []
            async for chunk in factory.astream(messages):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0].thinking == "Analyzing the problem..."
            assert chunks[1].content == "The answer is 42"

    @pytest.mark.asyncio
    async def test_astream_passes_stream_true_to_litellm(self, mock_settings) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN calling astream()
        THEN it should pass stream=True to litellm.acompletion
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    content = "Hi"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            # Consume the stream
            async for _ in factory.astream(messages):
                pass

            # Verify stream=True was passed
            mock_acompletion.assert_called_once()
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs.get("stream") is True

    @pytest.mark.asyncio
    async def test_astream_uses_factory_configuration(self, mock_settings) -> None:
        """
        GIVEN an LLMFactory with specific configuration
        WHEN calling astream()
        THEN it should use factory's model, temperature, etc.
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            api_key="test-key",
            temperature=0.5,
            max_tokens=2048,
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    content = "Hi"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            async for _ in factory.astream(messages):
                pass

            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 2048


# =============================================================================
# Phase 1: Streaming with Bulkhead Tests
# =============================================================================


@pytest.mark.xdist_group(name="llm_streaming")
class TestLLMFactoryAstreamBulkhead:
    """Tests for bulkhead integration with astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_astream_holds_bulkhead_slot(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN streaming is in progress
        THEN bulkhead slot should be held for entire stream duration
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            with patch("mcp_server_langgraph.llm.factory.get_provider_adaptive_bulkhead") as mock_bulkhead:
                mock_semaphore = AsyncMock()  # noqa: async-mock-config
                mock_semaphore.__aenter__ = AsyncMock(return_value=None)
                mock_semaphore.__aexit__ = AsyncMock(return_value=None)
                mock_bulkhead.return_value.get_semaphore.return_value = mock_semaphore

                async def mock_stream():
                    class MockDelta:
                        content = "Hi"
                        reasoning_content = None

                    class MockChoice:
                        delta = MockDelta()
                        finish_reason = "stop"

                    class MockChunk:
                        choices = [MockChoice()]

                    yield MockChunk()

                mock_acompletion.return_value = mock_stream()

                async for _ in factory.astream(messages):
                    pass

                # Bulkhead should have been acquired
                mock_bulkhead.assert_called()


# =============================================================================
# Phase 1: Streaming Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="llm_streaming")
class TestLLMFactoryAstreamErrors:
    """Tests for error handling in astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_astream_connection_error_raises_exception(self) -> None:
        """
        GIVEN a connection failure before streaming starts
        WHEN calling astream()
        THEN it should raise LLMProviderError
        """
        from mcp_server_langgraph.core.exceptions import LLMProviderError
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_acompletion.side_effect = Exception("Connection refused")

            with pytest.raises(LLMProviderError):
                async for _ in factory.astream(messages):
                    pass

    @pytest.mark.asyncio
    async def test_astream_mid_stream_error_propagates(self) -> None:
        """
        GIVEN a streaming response that fails mid-stream
        WHEN iterating over astream() result
        THEN the error should propagate to caller
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def failing_stream():
                class MockDelta:
                    content = "Starting..."
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = None

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()
                raise Exception("Stream interrupted")

            mock_acompletion.return_value = failing_stream()

            chunks = []
            with pytest.raises(Exception, match="Stream interrupted"):
                async for chunk in factory.astream(messages):
                    chunks.append(chunk)

            # Should have received at least one chunk before error
            assert len(chunks) >= 1


# =============================================================================
# Phase 2: Streaming-Aware Resilience Tests
# =============================================================================


@pytest.mark.xdist_group(name="llm_streaming_resilience")
class TestLLMFactoryAstreamFirstChunkTimeout:
    """Tests for first-chunk timeout in astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_astream_has_first_chunk_timeout_parameter(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN calling astream() with first_chunk_timeout
        THEN it should accept the parameter
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    content = "Hi"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            # Should not raise when passing first_chunk_timeout
            async for _ in factory.astream(messages, first_chunk_timeout=30.0):
                pass

    @pytest.mark.asyncio
    async def test_astream_first_chunk_timeout_raises_on_slow_response(self) -> None:
        """
        GIVEN a streaming response that takes too long for first chunk
        WHEN first_chunk_timeout is exceeded
        THEN it should raise LLMTimeoutError (wrapped TimeoutError)
        """
        import asyncio

        from mcp_server_langgraph.core.exceptions import LLMTimeoutError
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def slow_stream():
                # Simulate slow first chunk (intentionally long for timeout test)
                await asyncio.sleep(1.0)  # noqa: sleep-duration

                class MockDelta:
                    content = "Hi"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = slow_stream()

            with pytest.raises((LLMTimeoutError, TimeoutError, asyncio.TimeoutError)):
                async for _ in factory.astream(messages, first_chunk_timeout=0.1):
                    pass


@pytest.mark.xdist_group(name="llm_streaming_resilience")
class TestLLMFactoryAstreamPreFirstChunkRetry:
    """Tests for pre-first-chunk retry in astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_astream_retries_connection_error_before_first_chunk(self) -> None:
        """
        GIVEN a connection failure before first chunk
        WHEN retry is enabled
        THEN it should retry and succeed on second attempt
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        call_count = 0

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def success_stream():
                class MockDelta:
                    content = "Success!"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("Connection refused")
                return success_stream()

            mock_acompletion.side_effect = side_effect

            chunks = []
            async for chunk in factory.astream(messages, enable_retry=True, max_retries=2):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert chunks[0].content == "Success!"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_astream_does_not_retry_after_first_chunk(self) -> None:
        """
        GIVEN a failure after first chunk is received
        WHEN retry is enabled
        THEN it should NOT retry (error propagates immediately)
        """
        from mcp_server_langgraph.core.exceptions import LLMProviderError
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        call_count = 0

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def failing_after_first_stream():
                class MockDelta:
                    def __init__(self, content):
                        self.content = content
                        self.reasoning_content = None

                class MockChoice:
                    def __init__(self, content):
                        self.delta = MockDelta(content)
                        self.finish_reason = None

                class MockChunk:
                    def __init__(self, content):
                        self.choices = [MockChoice(content)]

                yield MockChunk("First")
                raise ConnectionError("Mid-stream failure")

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return failing_after_first_stream()

            mock_acompletion.side_effect = side_effect

            chunks = []
            # Errors after first chunk are wrapped in LLMProviderError
            with pytest.raises((LLMProviderError, ConnectionError)):
                async for chunk in factory.astream(messages, enable_retry=True, max_retries=3):
                    chunks.append(chunk)

            # Should have received one chunk before failure
            assert len(chunks) == 1
            # Should NOT have retried (only one call)
            assert call_count == 1


@pytest.mark.xdist_group(name="llm_streaming_resilience")
class TestLLMFactoryAstreamInterChunkTimeout:
    """Tests for inter-chunk timeout in astream()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_astream_has_inter_chunk_timeout_parameter(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN calling astream() with inter_chunk_timeout
        THEN it should accept the parameter
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    content = "Hi"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            # Should not raise when passing inter_chunk_timeout
            async for _ in factory.astream(messages, inter_chunk_timeout=10.0):
                pass

    @pytest.mark.asyncio
    async def test_astream_inter_chunk_timeout_raises_on_stalled_stream(self) -> None:
        """
        GIVEN a streaming response that stalls between chunks
        WHEN inter_chunk_timeout is exceeded
        THEN it should raise LLMTimeoutError (wrapped TimeoutError)
        """
        import asyncio

        from mcp_server_langgraph.core.exceptions import LLMTimeoutError
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        messages = [HumanMessage(content="Hello")]

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def stalling_stream():
                class MockDelta:
                    def __init__(self, content):
                        self.content = content
                        self.reasoning_content = None

                class MockChoice:
                    def __init__(self, content):
                        self.delta = MockDelta(content)
                        self.finish_reason = None

                class MockChunk:
                    def __init__(self, content):
                        self.choices = [MockChoice(content)]

                yield MockChunk("First")
                # Simulate stalled stream (intentionally long for timeout test)
                await asyncio.sleep(1.0)  # noqa: sleep-duration
                yield MockChunk("Second")

            mock_acompletion.return_value = stalling_stream()

            chunks = []
            with pytest.raises((LLMTimeoutError, TimeoutError, asyncio.TimeoutError)):
                async for chunk in factory.astream(messages, inter_chunk_timeout=0.1):
                    chunks.append(chunk)

            # Should have received first chunk before timeout
            assert len(chunks) == 1
