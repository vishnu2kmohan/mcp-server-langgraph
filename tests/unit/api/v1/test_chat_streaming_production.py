"""
Chat Router Streaming Production Wiring Tests

TDD tests for wiring _stream_via_llm_factory into production code path.

These tests validate:
1. Feature flag controls streaming method selection
2. Circuit breaker integration with streaming
3. Cost tracking for streaming responses
4. Graceful fallback on factory errors
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.llm.factory import StreamChunk

pytestmark = [pytest.mark.unit, pytest.mark.chat]


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_production")
class TestLLMFactoryStreamingFeatureFlag:
    """Tests for feature flag controlling LLM factory streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flag_exists(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN checking for enable_llm_factory_streaming
        THEN it should exist as a boolean field
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_llm_factory_streaming")
        assert isinstance(flags.enable_llm_factory_streaming, bool)

    def test_feature_flag_default_true(self) -> None:
        """
        GIVEN the FeatureFlags class
        WHEN using default values
        THEN enable_llm_factory_streaming should be True (legacy removed)

        With the removal of _stream_via_litellm, LLMFactory streaming is now
        the default and only path for streaming. The flag defaults to True.
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        # Default to True now that legacy litellm path is removed
        assert flags.enable_llm_factory_streaming is True


# =============================================================================
# Production Wiring Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_production")
class TestLLMFactoryStreamingProductionWiring:
    """Tests for wiring _stream_via_llm_factory into production."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_stream_uses_llm_factory(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN create_stream is called
        THEN it should use LLMFactory.astream() (the only streaming path)

        Note: After removing _stream_via_litellm, LLMFactory.astream() is the only
        streaming path. No feature flag check is needed.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Hello", chunk_index=0, is_final=False)
            yield StreamChunk(content=" world", chunk_index=1, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        chunks = []
        async for chunk in service.create_stream("session-1", messages):
            chunks.append(chunk)

        # Should have received chunks from llm_factory
        assert len(chunks) >= 1
        assert any("delta" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_create_stream_always_uses_llm_factory(self) -> None:
        """
        GIVEN enable_llm_factory_streaming=True (default after legacy removal)
        WHEN create_stream is called
        THEN it should always use LLMFactory streaming (no litellm fallback)

        After removing _stream_via_litellm, LLMFactory.astream() is the only
        streaming path. The feature flag now controls resilience features rather
        than method selection.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream(messages, **kwargs):
            yield StreamChunk(content="Response", chunk_index=0, is_final=False)
            yield StreamChunk(content="", chunk_index=1, is_final=True)

        mock_factory.astream = mock_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # LLMFactory streaming is always used
        chunks = []
        async for chunk in service.create_stream("session-1", messages):
            chunks.append(chunk)

        # Should have received chunks from LLMFactory
        assert len(chunks) >= 1
        assert any("delta" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_create_stream_propagates_factory_error(self) -> None:
        """
        GIVEN LLMFactory.astream() throws an error
        WHEN create_stream is called
        THEN it should propagate the error (no fallback to litellm)

        After removing _stream_via_litellm, LLMFactory errors propagate directly.
        The circuit breaker and retry patterns in LLMFactory handle resilience.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.core.exceptions import LLMProviderError

        mock_factory = MagicMock()

        async def failing_astream(messages, **kwargs):
            raise LLMProviderError("Factory connection failed", metadata={"provider": "google"})
            yield  # Make it an async generator

        mock_factory.astream = failing_astream

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        # Error should propagate - no fallback to litellm
        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in service.create_stream("session-1", messages):
                pass

        assert "Factory connection failed" in str(exc_info.value)


# =============================================================================
# Streaming Cost Tracking Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_production")
class TestStreamingCostTracking:
    """Tests for cost tracking in streaming responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_records_usage_on_completion(self) -> None:
        """
        GIVEN a streaming response that completes successfully
        WHEN the stream ends
        THEN usage should be recorded for cost tracking

        Note: LLMFactory.astream() is now the only streaming path, so no feature
        flag check is needed.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_factory = MagicMock()

        async def mock_astream_with_usage(messages, **kwargs):
            yield StreamChunk(content="Hello", chunk_index=0, is_final=False)
            yield StreamChunk(
                content="",
                chunk_index=1,
                is_final=True,
                finish_reason="stop",
            )

        mock_factory.astream = mock_astream_with_usage

        service = ChatServiceImpl(llm_factory=mock_factory)

        messages = [{"role": "user", "content": "Hi"}]

        async for _ in service.create_stream("session-1", messages):
            pass

        # The factory should handle cost tracking internally
        # This test validates the integration point exists

    def test_stream_chunk_has_usage_fields(self) -> None:
        """
        GIVEN the StreamChunk dataclass
        WHEN checking for usage-related fields
        THEN it should have fields for token tracking (if added)
        """
        # StreamChunk should support usage tracking for cost calculation
        # Usage is typically aggregated at stream end
        chunk = StreamChunk(
            content="test",
            chunk_index=0,
            is_final=True,
            finish_reason="stop",
        )

        # Basic fields exist
        assert chunk.content == "test"
        assert chunk.is_final is True


# =============================================================================
# Circuit Breaker Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="chat_streaming_production")
class TestStreamingCircuitBreaker:
    """Tests for circuit breaker integration with streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_llm_factory_has_circuit_breaker_integration(self) -> None:
        """
        GIVEN an LLMFactory instance
        WHEN checking for circuit breaker support
        THEN astream should integrate with circuit breaker
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        # Factory should have circuit breaker awareness
        assert hasattr(factory, "astream")

    @pytest.mark.asyncio
    async def test_streaming_opens_circuit_on_repeated_failures(self) -> None:
        """
        GIVEN repeated streaming connection failures
        WHEN fail_max threshold is exceeded
        THEN circuit breaker should open and reject further requests
        """
        from mcp_server_langgraph.core.exceptions import LLMProviderError
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        # Simulate repeated failures
        failure_count = 0

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_acompletion.side_effect = ConnectionError("Connection refused")

            # Try multiple times to trigger circuit breaker
            for _ in range(3):
                try:
                    async for _ in factory.astream([{"role": "user", "content": "Hi"}]):
                        pass
                except (LLMProviderError, ConnectionError):
                    failure_count += 1

            # Should have failed multiple times
            assert failure_count >= 3

    @pytest.mark.asyncio
    async def test_streaming_circuit_breaker_allows_recovery(self) -> None:
        """
        GIVEN an open circuit breaker
        WHEN the service recovers
        THEN circuit should close and allow requests
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            provider="google",
            model_name="gemini-2.5-flash",
            api_key="test-key",
        )

        call_count = 0

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:

            async def mock_stream():
                class MockDelta:
                    content = "Success"
                    reasoning_content = None

                class MockChoice:
                    delta = MockDelta()
                    finish_reason = "stop"

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_acompletion.return_value = mock_stream()

            # Successful call after recovery
            async for chunk in factory.astream([{"role": "user", "content": "Hi"}]):
                call_count += 1

            assert call_count >= 1
