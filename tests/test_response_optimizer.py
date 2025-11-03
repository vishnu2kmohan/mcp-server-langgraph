"""
Tests for ResponseOptimizer utility

Tests token counting, response truncation, format control,
and high-signal information extraction.
"""

import pytest

from mcp_server_langgraph.utils.response_optimizer import (
    DEFAULT_CONCISE_TOKENS,
    DEFAULT_DETAILED_TOKENS,
    MAX_RESPONSE_TOKENS,
    ResponseOptimizer,
    count_tokens,
    extract_high_signal,
    format_response,
    truncate_response,
)


@pytest.mark.unit
class TestResponseOptimizer:
    """Test ResponseOptimizer class."""

    def test_initialization(self):
        """Test ResponseOptimizer initialization."""
        optimizer = ResponseOptimizer()
        assert optimizer.encoding is not None

    def test_initialization_with_model(self):
        """Test ResponseOptimizer with specific model."""
        optimizer = ResponseOptimizer(model="gpt-4")
        assert optimizer.encoding is not None

    def test_count_tokens_simple(self):
        """Test token counting with simple text."""
        optimizer = ResponseOptimizer()
        text = "Hello, world!"
        token_count = optimizer.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_empty(self):
        """Test token counting with empty string."""
        optimizer = ResponseOptimizer()
        token_count = optimizer.count_tokens("")
        assert token_count == 0

    def test_count_tokens_long_text(self):
        """Test token counting with long text."""
        optimizer = ResponseOptimizer()
        # Generate a long text (approximately 1000 tokens)
        text = "Hello world! " * 500
        token_count = optimizer.count_tokens(text)
        assert token_count > 500  # Should be more than 500 tokens

    def test_truncate_response_no_truncation_needed(self):
        """Test truncation when text is under limit."""
        optimizer = ResponseOptimizer()
        text = "Short text that doesn't need truncation."
        truncated, was_truncated = optimizer.truncate_response(text, max_tokens=1000)
        assert truncated == text
        assert was_truncated is False

    def test_truncate_response_with_truncation(self):
        """Test truncation when text exceeds limit."""
        optimizer = ResponseOptimizer()
        # Create text that will definitely exceed limit
        text = "Hello world! " * 1000  # ~2000 tokens
        truncated, was_truncated = optimizer.truncate_response(text, max_tokens=100)
        assert len(truncated) < len(text)
        assert was_truncated is True
        assert "[Response truncated" in truncated

    def test_truncate_response_custom_message(self):
        """Test truncation with custom truncation message."""
        optimizer = ResponseOptimizer()
        text = "Hello world! " * 1000
        custom_msg = "\n\n[Custom truncation message]"
        truncated, was_truncated = optimizer.truncate_response(text, max_tokens=100, truncation_message=custom_msg)
        assert was_truncated is True
        assert custom_msg in truncated

    def test_format_response_concise(self):
        """Test format_response with concise format."""
        optimizer = ResponseOptimizer()
        # Create text longer than concise limit
        text = "Word " * 1000  # ~1000 tokens
        formatted = optimizer.format_response(text, format_type="concise")
        # Should be truncated to concise limit
        token_count = optimizer.count_tokens(formatted)
        assert token_count <= DEFAULT_CONCISE_TOKENS + 50  # Allow some overhead for truncation message

    def test_format_response_detailed(self):
        """Test format_response with detailed format."""
        optimizer = ResponseOptimizer()
        # Create text longer than detailed limit but shorter than max
        text = "Word " * 2500  # ~2500 tokens
        formatted = optimizer.format_response(text, format_type="detailed")
        # Should be truncated to detailed limit
        token_count = optimizer.count_tokens(formatted)
        assert token_count <= DEFAULT_DETAILED_TOKENS + 100  # Allow overhead

    def test_format_response_short_text(self):
        """Test format_response with text shorter than limits."""
        optimizer = ResponseOptimizer()
        text = "Short text."
        formatted_concise = optimizer.format_response(text, format_type="concise")
        formatted_detailed = optimizer.format_response(text, format_type="detailed")
        # Should not be truncated
        assert formatted_concise == text
        assert formatted_detailed == text

    def test_format_response_custom_max_tokens(self):
        """Test format_response with custom max_tokens."""
        optimizer = ResponseOptimizer()
        text = "Word " * 1000
        formatted = optimizer.format_response(text, format_type="concise", max_tokens=50)
        token_count = optimizer.count_tokens(formatted)
        assert token_count <= 100  # 50 + overhead

    def test_extract_high_signal_basic(self):
        """Test high-signal extraction with basic data."""
        optimizer = ResponseOptimizer()
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "mime_type": "application/json",
            "created_at": "2025-10-17",
        }
        filtered = optimizer.extract_high_signal(data)
        # Should keep high-signal fields
        assert "name" in filtered
        assert "email" in filtered
        assert "created_at" in filtered
        # Should remove low-signal fields
        assert "uuid" not in filtered
        assert "mime_type" not in filtered

    def test_extract_high_signal_custom_exclude(self):
        """Test high-signal extraction with custom exclude list."""
        optimizer = ResponseOptimizer()
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "password_hash": "abc123",
            "internal_id": "xyz789",
        }
        filtered = optimizer.extract_high_signal(data, exclude_fields=["password_hash", "email"])
        assert "name" in filtered
        assert "email" not in filtered  # Custom exclusion
        assert "password_hash" not in filtered  # Custom exclusion
        assert "internal_id" not in filtered  # Default exclusion

    def test_extract_high_signal_empty_data(self):
        """Test high-signal extraction with empty data."""
        optimizer = ResponseOptimizer()
        filtered = optimizer.extract_high_signal({})
        assert filtered == {}


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_count_tokens_global(self):
        """Test global count_tokens function."""
        token_count = count_tokens("Hello, world!")
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_truncate_response_global(self):
        """Test global truncate_response function."""
        text = "Hello world! " * 1000
        truncated, was_truncated = truncate_response(text, max_tokens=100)
        assert was_truncated is True
        assert len(truncated) < len(text)

    def test_format_response_global(self):
        """Test global format_response function."""
        text = "Word " * 1000
        formatted = format_response(text, format_type="concise")
        token_count = count_tokens(formatted)
        assert token_count <= DEFAULT_CONCISE_TOKENS + 50

    def test_extract_high_signal_global(self):
        """Test global extract_high_signal function."""
        data = {
            "name": "Test",
            "uuid": "123",
        }
        filtered = extract_high_signal(data)
        assert "name" in filtered
        assert "uuid" not in filtered


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_text(self):
        """Test with text much longer than max tokens."""
        optimizer = ResponseOptimizer()
        # Create extremely long text
        text = "Word " * 50000  # ~50k tokens
        truncated, was_truncated = optimizer.truncate_response(text, max_tokens=MAX_RESPONSE_TOKENS)
        assert was_truncated is True
        token_count = optimizer.count_tokens(truncated)
        # Should be under max tokens (with some overhead for truncation message)
        assert token_count <= MAX_RESPONSE_TOKENS + 100

    def test_unicode_text(self):
        """Test with Unicode characters."""
        optimizer = ResponseOptimizer()
        text = "Hello 世界! 🌍 Émojis and spëcial çharacters"
        token_count = optimizer.count_tokens(text)
        assert token_count > 0

    def test_special_characters(self):
        """Test with special characters and markdown."""
        optimizer = ResponseOptimizer()
        text = """
        # Header
        - Bullet point
        **Bold text**
        `code block`
        [Link](http://example.com)
        """
        token_count = optimizer.count_tokens(text)
        assert token_count > 0

    def test_truncation_preserves_text_beginning(self):
        """Test that truncation keeps the beginning of text."""
        optimizer = ResponseOptimizer()
        text = "BEGINNING " + ("middle " * 1000) + " END"
        truncated, was_truncated = optimizer.truncate_response(text, max_tokens=50)
        assert was_truncated is True
        assert "BEGINNING" in truncated
        # END should likely not be in truncated text since we truncate from the end
        assert "END" not in truncated


class TestPerformance:
    """Test performance characteristics."""

    def test_token_counting_performance(self):
        """Test that token counting is reasonably fast."""
        import time

        optimizer = ResponseOptimizer()
        text = "Word " * 10000  # ~10k tokens

        start = time.time()
        for _ in range(100):
            optimizer.count_tokens(text)
        elapsed = time.time() - start

        # Should complete 100 iterations in less than 1 second
        assert elapsed < 1.0, f"Token counting too slow: {elapsed:.2f}s for 100 iterations"

    def test_truncation_performance(self):
        """Test that truncation is reasonably fast."""
        import time

        optimizer = ResponseOptimizer()
        text = "Word " * 10000

        start = time.time()
        for _ in range(10):
            optimizer.truncate_response(text, max_tokens=100)
        elapsed = time.time() - start

        # Should complete 10 iterations in less than 1 second
        assert elapsed < 1.0, f"Truncation too slow: {elapsed:.2f}s for 10 iterations"


@pytest.mark.parametrize(
    "text,format_type,expected_truncated",
    [
        ("Short text", "concise", False),
        ("Short text", "detailed", False),
        ("Word " * 1000, "concise", True),
        ("Word " * 3000, "detailed", True),
    ],
)
def test_format_response_parametrized(text, format_type, expected_truncated):
    """Parametrized test for format_response."""
    optimizer = ResponseOptimizer()
    formatted = optimizer.format_response(text, format_type=format_type)

    if expected_truncated:
        assert "[Response truncated" in formatted or len(formatted) < len(text)
    else:
        assert formatted == text


@pytest.mark.parametrize(
    "data,should_contain,should_not_contain",
    [
        (
            {"name": "Test", "uuid": "123"},
            ["name"],
            ["uuid"],
        ),
        (
            {"title": "Doc", "mime_type": "text/plain", "content": "Hello"},
            ["title", "content"],
            ["mime_type"],
        ),
        (
            {"user_id": "alice", "guid": "xyz", "internal_id": "123"},
            ["user_id"],
            ["guid", "internal_id"],
        ),
    ],
)
def test_extract_high_signal_parametrized(data, should_contain, should_not_contain):
    """Parametrized test for extract_high_signal."""
    optimizer = ResponseOptimizer()
    filtered = optimizer.extract_high_signal(data)

    for field in should_contain:
        assert field in filtered, f"Expected {field} to be in filtered data"

    for field in should_not_contain:
        assert field not in filtered, f"Expected {field} to NOT be in filtered data"


@pytest.mark.unit
class TestLiteLLMTokenCounting:
    """
    Test LiteLLM-based token counting for model-aware accuracy.

    TDD RED phase: Tests written FIRST to define expected behavior for LiteLLM integration.
    Will fail until tiktoken is replaced with litellm.token_counter().
    """

    def test_count_tokens_openai_model(self):
        """Test token counting for OpenAI models (GPT-4)"""
        optimizer = ResponseOptimizer(model="gpt-4")
        text = "Hello, world!"
        token_count = optimizer.count_tokens(text)

        # Should be accurate for GPT-4
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_gemini_model(self):
        """
        Test token counting for Gemini models.

        RED: Will be more accurate after switching to LiteLLM.
        Currently uses tiktoken which approximates Gemini tokens.
        """
        optimizer = ResponseOptimizer(model="gemini-2.5-flash")
        text = "The quick brown fox jumps over the lazy dog."
        token_count = optimizer.count_tokens(text)

        # Token count should be reasonable (not negative, not extremely high)
        assert 0 < token_count < 100

    def test_count_tokens_claude_model(self):
        """
        Test token counting for Claude models.

        RED: Will be more accurate after switching to LiteLLM.
        """
        optimizer = ResponseOptimizer(model="claude-sonnet-4-5-20250929")
        text = "Test message for Claude model token counting."
        token_count = optimizer.count_tokens(text)

        assert token_count > 0

    def test_count_tokens_unknown_model_fallback(self):
        """Test fallback behavior for unknown models"""
        optimizer = ResponseOptimizer(model="unknown-model-xyz")
        text = "Test text"
        token_count = optimizer.count_tokens(text)

        # Should still work with fallback encoding
        assert token_count > 0

    def test_model_specific_token_accuracy(self):
        """
        Test that different models may have different token counts.

        After LiteLLM integration, models should use their native tokenizers.
        """
        text = "This is a test sentence with some words in it."

        # Different models may tokenize differently
        gpt4_optimizer = ResponseOptimizer(model="gpt-4")
        gemini_optimizer = ResponseOptimizer(model="gemini-2.5-flash")
        claude_optimizer = ResponseOptimizer(model="claude-sonnet-4-5-20250929")

        gpt4_tokens = gpt4_optimizer.count_tokens(text)
        gemini_tokens = gemini_optimizer.count_tokens(text)
        claude_tokens = claude_optimizer.count_tokens(text)

        # All should be non-zero
        assert gpt4_tokens > 0
        assert gemini_tokens > 0
        assert claude_tokens > 0

        # Token counts should be in similar range (within 50% of each other)
        # After LiteLLM, they may vary but should be reasonable
        min_tokens = min(gpt4_tokens, gemini_tokens, claude_tokens)
        max_tokens = max(gpt4_tokens, gemini_tokens, claude_tokens)
        assert max_tokens <= min_tokens * 1.5, "Token counts vary too much across models"
