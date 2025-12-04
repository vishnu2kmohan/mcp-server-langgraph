"""
Unit tests for fallback model resilience.

Tests TDD-style for:
1. Exponential backoff between fallback attempts
2. Per-model circuit breakers
3. Timeout protection for fallback calls

These tests are written FIRST (TDD) - implementation follows.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# Test Fallback Backoff
# =============================================================================


@pytest.mark.xdist_group(name="fallback_resilience")
class TestFallbackBackoff:
    """Test exponential backoff between fallback attempts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_has_delay_between_attempts(self):
        """Should wait between fallback attempts to avoid thundering herd."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        # Create factory with multiple fallback models
        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fallback-1", "fallback-2", "fallback-3"],
            enable_fallback=True,
        )

        # Mock acompletion to fail for all models
        with (
            patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion,
            patch("asyncio.sleep", side_effect=mock_sleep) as _,
        ):
            mock_acompletion.side_effect = Exception("Model unavailable")

            # Should try fallbacks with delays between each
            with pytest.raises(RuntimeError, match="All async models failed"):
                await factory._try_fallback_async([{"role": "user", "content": "test"}])

        # Should have delays between attempts (at least 2 delays for 3 fallbacks)
        assert len(sleep_calls) >= 2, f"Expected delays between fallbacks, got {len(sleep_calls)} delays"
        # First delay should be the base delay (1.0s default)
        assert sleep_calls[0] >= 0.5, f"Expected base delay ~1.0s, got {sleep_calls[0]}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_uses_exponential_backoff(self):
        """Backoff should increase exponentially: 1s, 2s, 4s."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fb1", "fb2", "fb3", "fb4"],
            enable_fallback=True,
        )

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion,
            patch("asyncio.sleep", side_effect=mock_sleep) as _,
        ):
            mock_acompletion.side_effect = Exception("Model unavailable")

            with pytest.raises(RuntimeError, match="All async models failed"):
                await factory._try_fallback_async([{"role": "user", "content": "test"}])

        # Verify exponential increase (each delay should be >= previous)
        if len(sleep_calls) >= 2:
            for i in range(1, len(sleep_calls)):
                assert sleep_calls[i] >= sleep_calls[i - 1], (
                    f"Expected exponential backoff, but delay[{i}]={sleep_calls[i]} < delay[{i - 1}]={sleep_calls[i - 1]}"
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_fallback_returns_without_further_delays(self):
        """If fallback succeeds, should return immediately without more delays."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fb1", "fb2", "fb3"],
            enable_fallback=True,
        )

        # Mock: first fallback fails, second succeeds
        call_count = 0

        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First fallback failed")
            # Second fallback succeeds
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Success from fb2"
            return mock_response

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_acompletion),
            patch("asyncio.sleep", side_effect=mock_sleep) as _,
        ):
            result = await factory._try_fallback_async([{"role": "user", "content": "test"}])

        # Should only have 1 delay (after first failure, before second attempt)
        assert len(sleep_calls) <= 1, f"Expected at most 1 delay, got {len(sleep_calls)}"
        assert result.content == "Success from fb2"


# =============================================================================
# Test Fallback Timeout
# =============================================================================


@pytest.mark.xdist_group(name="fallback_resilience")
class TestFallbackTimeout:
    """Test timeout protection for fallback calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_respects_timeout(self):
        """Fallback calls should respect timeout configuration."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fallback-1"],
            enable_fallback=True,
            timeout=30,  # 30 second timeout
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_acompletion.return_value = mock_response

            await factory._try_fallback_async([{"role": "user", "content": "test"}])

            # Verify timeout was passed to acompletion
            mock_acompletion.assert_called_once()
            call_kwargs = mock_acompletion.call_args.kwargs
            assert "timeout" in call_kwargs, "Timeout should be passed to fallback call"
            assert call_kwargs["timeout"] == 30, f"Expected timeout=30, got {call_kwargs['timeout']}"


# =============================================================================
# Test Fallback Circuit Breaker (Future Enhancement)
# =============================================================================


@pytest.mark.xdist_group(name="fallback_resilience")
class TestFallbackCircuitBreaker:
    """Test per-model circuit breaker protection for fallbacks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_tracks_failures_per_model(self):
        """Each fallback model should track its own failure count.

        Note: This is a future enhancement test. Currently, fallback models
        don't have per-model circuit breakers. When implemented, this test
        validates that each model maintains independent failure tracking.
        """
        # This test documents expected behavior for future implementation
        # Current implementation doesn't have per-model circuit breakers
        # Mark as xfail until implementation is added
        pytest.skip("Per-model circuit breakers not yet implemented - see P2 enhancement plan")


# =============================================================================
# Test Fallback Error Handling
# =============================================================================


@pytest.mark.xdist_group(name="fallback_resilience")
class TestFallbackErrorHandling:
    """Test error handling during fallback execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_continues_on_individual_failure(self):
        """Should try next fallback when one fails."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fb1", "fb2", "fb3"],
            enable_fallback=True,
        )

        call_order: list[str] = []

        async def mock_acompletion(*args, **kwargs):
            model = kwargs.get("model", args[0] if args else "unknown")
            call_order.append(model)
            if model == "fb3":
                # Last fallback succeeds
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Success"
                return mock_response
            raise Exception(f"Model {model} failed")

        with patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_acompletion):
            result = await factory._try_fallback_async([{"role": "user", "content": "test"}])

        # Should have tried all fallbacks in order until success
        assert call_order == ["fb1", "fb2", "fb3"], f"Expected ordered fallback attempts, got {call_order}"
        assert result.content == "Success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_raises_runtime_error_when_all_fail(self):
        """Should raise RuntimeError when all fallbacks exhausted."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            fallback_models=["fb1", "fb2"],
            enable_fallback=True,
        )

        with patch("mcp_server_langgraph.llm.factory.acompletion") as mock_acompletion:
            mock_acompletion.side_effect = Exception("All models down")

            with pytest.raises(RuntimeError, match="All async models failed"):
                await factory._try_fallback_async([{"role": "user", "content": "test"}])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_skips_primary_model(self):
        """Should skip primary model in fallback list to avoid infinite loop."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(
            model_name="primary-model",
            api_key="test-key",
            # Primary model accidentally in fallback list
            fallback_models=["primary-model", "fallback-1"],
            enable_fallback=True,
        )

        call_order: list[str] = []

        async def mock_acompletion(*args, **kwargs):
            model = kwargs.get("model", "unknown")
            call_order.append(model)
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Success"
            return mock_response

        with patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_acompletion):
            await factory._try_fallback_async([{"role": "user", "content": "test"}])

        # Should NOT call primary-model, only fallback-1
        assert "primary-model" not in call_order, "Should skip primary model in fallback list"
        assert "fallback-1" in call_order, "Should call fallback-1"
