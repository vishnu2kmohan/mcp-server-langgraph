"""
Unit tests for enhanced retry logic with overload (529) error handling.

Tests TDD-style for:
1. Jitter strategies (simple, full, decorrelated)
2. Retry-After header parsing (RFC 7231)
3. Overload error detection (529 status, "overloaded" message)
4. Extended retry behavior for overload scenarios

These tests are written FIRST (TDD) - implementation follows.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# Test Jitter Strategies
# =============================================================================


@pytest.mark.xdist_group(name="test_jitter_strategies")
class TestJitterStrategies:
    """Test jitter calculation strategies."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_simple_jitter_within_bounds(self):
        """Simple jitter should be within +/- 20% of base delay."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import calculate_jitter_delay

        base_delay = 10.0
        max_delay = 60.0

        # Run multiple times to test randomness bounds
        for _ in range(100):
            result = calculate_jitter_delay(
                base_delay=base_delay,
                prev_delay=None,
                max_delay=max_delay,
                strategy=JitterStrategy.SIMPLE,
            )
            # Simple jitter: +/- 20%
            assert 8.0 <= result <= 12.0, f"Expected 8-12, got {result}"

    @pytest.mark.unit
    def test_full_jitter_within_bounds(self):
        """Full jitter should be between 0 and base delay."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import calculate_jitter_delay

        base_delay = 10.0
        max_delay = 60.0

        for _ in range(100):
            result = calculate_jitter_delay(
                base_delay=base_delay,
                prev_delay=None,
                max_delay=max_delay,
                strategy=JitterStrategy.FULL,
            )
            # Full jitter: random(0, delay)
            assert 0.0 <= result <= base_delay, f"Expected 0-{base_delay}, got {result}"

    @pytest.mark.unit
    def test_decorrelated_jitter_uses_prev_delay(self):
        """Decorrelated jitter should use previous delay for calculation."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import calculate_jitter_delay

        base_delay = 5.0
        prev_delay = 10.0
        max_delay = 60.0

        for _ in range(100):
            result = calculate_jitter_delay(
                base_delay=base_delay,
                prev_delay=prev_delay,
                max_delay=max_delay,
                strategy=JitterStrategy.DECORRELATED,
            )
            # Decorrelated: random(base, prev_delay * 3) capped at max
            # Range: 5.0 to min(60, 30) = 5.0 to 30.0
            assert base_delay <= result <= 30.0, f"Expected {base_delay}-30, got {result}"

    @pytest.mark.unit
    def test_decorrelated_jitter_respects_max(self):
        """Decorrelated jitter should not exceed max delay."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import calculate_jitter_delay

        base_delay = 5.0
        prev_delay = 50.0  # prev * 3 = 150, way over max
        max_delay = 60.0

        for _ in range(100):
            result = calculate_jitter_delay(
                base_delay=base_delay,
                prev_delay=prev_delay,
                max_delay=max_delay,
                strategy=JitterStrategy.DECORRELATED,
            )
            assert result <= max_delay, f"Expected <= {max_delay}, got {result}"

    @pytest.mark.unit
    def test_decorrelated_jitter_uses_base_when_no_prev(self):
        """Decorrelated jitter should use base delay when prev_delay is None."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import calculate_jitter_delay

        base_delay = 5.0
        max_delay = 60.0

        for _ in range(100):
            result = calculate_jitter_delay(
                base_delay=base_delay,
                prev_delay=None,  # No previous delay
                max_delay=max_delay,
                strategy=JitterStrategy.DECORRELATED,
            )
            # When no prev, uses base as prev: random(base, base * 3)
            assert base_delay <= result <= 15.0, f"Expected {base_delay}-15, got {result}"


# =============================================================================
# Test Retry-After Header Parsing
# =============================================================================


@pytest.mark.xdist_group(name="test_retry_after_parsing")
class TestRetryAfterParsing:
    """Test Retry-After header parsing per RFC 7231."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_parse_integer_seconds(self):
        """Should parse integer seconds correctly."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        result = parse_retry_after(60)
        assert result == 60.0

    @pytest.mark.unit
    def test_parse_string_seconds(self):
        """Should parse string integer correctly."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        result = parse_retry_after("120")
        assert result == 120.0

    @pytest.mark.unit
    def test_parse_float_string(self):
        """Should parse float string correctly."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        result = parse_retry_after("30.5")
        assert result == 30.5

    @pytest.mark.unit
    def test_parse_http_date(self):
        """Should parse HTTP-date format correctly."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        # HTTP-date format per RFC 7231
        # Use a future date to ensure positive delta
        future_date = "Wed, 31 Dec 2025 23:59:59 GMT"

        result = parse_retry_after(future_date)

        # Result should be a positive number (seconds until that time)
        assert result is not None
        assert result >= 0

    @pytest.mark.unit
    def test_parse_none_returns_none(self):
        """Should return None for None input."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        result = parse_retry_after(None)
        assert result is None

    @pytest.mark.unit
    def test_parse_invalid_returns_none(self):
        """Should return None for invalid values."""
        from mcp_server_langgraph.resilience.retry import parse_retry_after

        assert parse_retry_after("not-a-number") is None
        assert parse_retry_after("invalid-date-format") is None
        assert parse_retry_after("") is None

    @pytest.mark.unit
    def test_extract_from_httpx_response(self):
        """Should extract Retry-After from httpx exception response."""
        from mcp_server_langgraph.resilience.retry import extract_retry_after_from_exception

        # Create mock httpx exception with response headers
        # Use a real dict for headers to ensure .get() works correctly
        class MockResponse:
            headers = {"Retry-After": "60"}

        class MockException(Exception):
            response = MockResponse()

        result = extract_retry_after_from_exception(MockException())
        assert result == 60.0

    @pytest.mark.unit
    def test_extract_from_litellm_headers(self):
        """Should extract Retry-After from LiteLLM headers attribute."""
        from mcp_server_langgraph.resilience.retry import extract_retry_after_from_exception

        # LiteLLM exceptions may have llm_provider_response_headers
        class MockException(Exception):
            response = None
            llm_provider_response_headers = {"retry-after": "90"}

        result = extract_retry_after_from_exception(MockException())
        assert result == 90.0

    @pytest.mark.unit
    def test_extract_returns_none_when_not_present(self):
        """Should return None when Retry-After is not present."""
        from mcp_server_langgraph.resilience.retry import extract_retry_after_from_exception

        class MockException(Exception):
            response = None
            llm_provider_response_headers = None

        result = extract_retry_after_from_exception(MockException())
        assert result is None


# =============================================================================
# Test Overload Detection
# =============================================================================


@pytest.mark.xdist_group(name="test_overload_detection")
class TestOverloadDetection:
    """Test overload error detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_detect_529_status_code(self):
        """Should detect 529 status code as overload."""
        from mcp_server_langgraph.resilience.retry import is_overload_error

        mock_exception = MagicMock()
        mock_exception.status_code = 529

        assert is_overload_error(mock_exception) is True

    @pytest.mark.unit
    def test_detect_overloaded_message(self):
        """Should detect 'overloaded' in error message."""
        from mcp_server_langgraph.resilience.retry import is_overload_error

        exception = Exception("Service is overloaded, please try again")

        assert is_overload_error(exception) is True

    @pytest.mark.unit
    def test_detect_overload_error_type(self):
        """Should detect LLMOverloadError type."""
        from mcp_server_langgraph.core.exceptions import LLMOverloadError
        from mcp_server_langgraph.resilience.retry import is_overload_error

        exception = LLMOverloadError(message="Provider overloaded")

        assert is_overload_error(exception) is True

    @pytest.mark.unit
    def test_detect_503_with_overload_message(self):
        """Should detect 503 + overload message as overload."""
        from mcp_server_langgraph.resilience.retry import is_overload_error

        mock_exception = MagicMock()
        mock_exception.status_code = 503
        mock_exception.__str__ = lambda self: "Service temporarily unavailable - overloaded"

        assert is_overload_error(mock_exception) is True

    @pytest.mark.unit
    def test_not_overload_for_regular_errors(self):
        """Should return False for regular errors."""
        from mcp_server_langgraph.resilience.retry import is_overload_error

        # Regular ValueError
        assert is_overload_error(ValueError("Some error")) is False

        # Regular 500 error
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.__str__ = lambda self: "Internal server error"
        assert is_overload_error(mock_500) is False

        # 429 rate limit (different from overload)
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.__str__ = lambda self: "Rate limit exceeded"
        assert is_overload_error(mock_429) is False

    @pytest.mark.unit
    def test_detect_529_in_message(self):
        """Should detect '529' in error message."""
        from mcp_server_langgraph.resilience.retry import is_overload_error

        exception = Exception("HTTP 529: Service overloaded")

        assert is_overload_error(exception) is True


# =============================================================================
# Test Overload Retry Configuration
# =============================================================================


@pytest.mark.xdist_group(name="test_overload_config")
class TestOverloadRetryConfig:
    """Test overload-specific retry configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_overload_config_defaults(self):
        """Test default values for OverloadRetryConfig."""
        from mcp_server_langgraph.resilience.config import JitterStrategy, OverloadRetryConfig

        config = OverloadRetryConfig()

        assert config.max_attempts == 6
        assert config.exponential_base == 2.0
        assert config.exponential_max == 60.0
        assert config.initial_delay == 5.0
        assert config.jitter_strategy == JitterStrategy.DECORRELATED
        assert config.honor_retry_after is True
        assert config.retry_after_max == 120.0

    @pytest.mark.unit
    def test_jitter_strategy_enum_values(self):
        """Test JitterStrategy enum has expected values."""
        from mcp_server_langgraph.resilience.config import JitterStrategy

        assert JitterStrategy.SIMPLE.value == "simple"
        assert JitterStrategy.FULL.value == "full"
        assert JitterStrategy.DECORRELATED.value == "decorrelated"

    @pytest.mark.unit
    def test_overload_config_from_env(self):
        """Test OverloadRetryConfig loads from environment variables."""
        from mcp_server_langgraph.resilience.config import ResilienceConfig

        with patch.dict(
            "os.environ",
            {
                "RETRY_OVERLOAD_MAX_ATTEMPTS": "8",
                "RETRY_OVERLOAD_EXPONENTIAL_MAX": "90.0",
                "RETRY_OVERLOAD_INITIAL_DELAY": "10.0",
                "RETRY_OVERLOAD_JITTER_STRATEGY": "full",
                "RETRY_OVERLOAD_HONOR_RETRY_AFTER": "false",
                "RETRY_OVERLOAD_RETRY_AFTER_MAX": "180.0",
            },
        ):
            config = ResilienceConfig.from_env()

            assert config.retry.overload.max_attempts == 8
            assert config.retry.overload.exponential_max == 90.0
            assert config.retry.overload.initial_delay == 10.0
            assert config.retry.overload.jitter_strategy.value == "full"
            assert config.retry.overload.honor_retry_after is False
            assert config.retry.overload.retry_after_max == 180.0


# =============================================================================
# Test LLMOverloadError Exception
# =============================================================================


@pytest.mark.xdist_group(name="test_llm_overload_error")
class TestLLMOverloadError:
    """Test LLMOverloadError exception class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_llm_overload_error_defaults(self):
        """Test LLMOverloadError default values."""
        from mcp_server_langgraph.core.exceptions import LLMOverloadError, RetryPolicy

        error = LLMOverloadError()

        assert error.default_status_code == 529
        assert error.default_error_code == "external.llm.overloaded"
        assert error.default_retry_policy == RetryPolicy.ALWAYS

    @pytest.mark.unit
    def test_llm_overload_error_with_retry_after(self):
        """Test LLMOverloadError stores retry_after value."""
        from mcp_server_langgraph.core.exceptions import LLMOverloadError

        error = LLMOverloadError(
            message="Provider overloaded",
            retry_after=60,
            metadata={"model": "claude-sonnet-4-5"},
        )

        assert error.retry_after == 60
        assert error.metadata["model"] == "claude-sonnet-4-5"

    @pytest.mark.unit
    def test_llm_overload_error_inherits_from_llm_provider_error(self):
        """Test LLMOverloadError inherits from LLMProviderError."""
        from mcp_server_langgraph.core.exceptions import LLMOverloadError, LLMProviderError

        error = LLMOverloadError()

        assert isinstance(error, LLMProviderError)


# =============================================================================
# Test Overload-Aware Retry Behavior
# =============================================================================


@pytest.mark.xdist_group(name="test_overload_retry_behavior")
class TestOverloadRetryBehavior:
    """Test retry behavior for overload scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_overload_aware_parameter_accepted(self):
        """Should accept overload_aware parameter without error."""
        from mcp_server_langgraph.resilience.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_attempts=2, overload_aware=True)
        async def simple_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Fail once")
            return "success"

        result = await simple_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_jitter_strategy_parameter_accepted(self):
        """Should accept jitter_strategy parameter without error."""
        from mcp_server_langgraph.resilience.config import JitterStrategy
        from mcp_server_langgraph.resilience.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_attempts=2, jitter_strategy=JitterStrategy.DECORRELATED)
        async def simple_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Fail once")
            return "success"

        result = await simple_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_overload_error_is_retried(self):
        """Should retry LLMOverloadError like other transient errors."""
        from mcp_server_langgraph.core.exceptions import LLMOverloadError
        from mcp_server_langgraph.resilience.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def overload_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMOverloadError("Overloaded")
            return "success"

        result = await overload_func()
        assert result == "success"
        assert call_count == 2  # First attempt failed, second succeeded

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_backward_compatible_for_other_errors(self):
        """Should use standard config for non-overload errors."""
        from mcp_server_langgraph.core.exceptions import RetryExhaustedError
        from mcp_server_langgraph.resilience.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_attempts=3, overload_aware=True)
        async def regular_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Regular error")

        with pytest.raises(RetryExhaustedError):
            await regular_error_func()

        # Should use standard config (3 attempts)
        assert call_count == 3
