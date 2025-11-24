"""
Response optimization utilities for token-efficient tool responses.

Implements Anthropic's best practices for writing tools for agents:
- Token counting and truncation
- Response format control (concise vs detailed)
- High-signal information filtering
"""

from typing import Any, Literal

import litellm

from mcp_server_langgraph.observability.telemetry import logger

# Maximum tokens per response (Anthropic recommendation: ~25k tokens)
MAX_RESPONSE_TOKENS = 25000
DEFAULT_CONCISE_TOKENS = 500
DEFAULT_DETAILED_TOKENS = 2000


class ResponseOptimizer:
    """
    Utility class for optimizing tool responses for agent consumption.

    Features:
    - Token counting using tiktoken
    - Response truncation with helpful messages
    - Format control (concise vs detailed)
    - High-signal information extraction
    """

    def __init__(self, model: str = "gpt-4") -> None:
        """
        Initialize response optimizer.

        Args:
            model: Model name for token encoding (default: gpt-4)
        """
        self.model = model
        # Removed logger call here to avoid observability initialization issues at module import time
        # Logger will be used when methods are actually called

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using LiteLLM model-aware token counting.

        SECURITY (OpenAI Codex Finding #4):
        Uses litellm.token_counter() which now supports Gemini, GPT, Claude, and other models.
        Fallback to len(text)//4 is kept for compatibility but logs warning for monitoring.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens

        Note:
            - Gemini models: Supported by litellm (tested)
            - OpenAI models: Supported via tiktoken (tested)
            - Claude models: Supported by litellm (tested)
            - Fallback: len(text)//4 (conservative, but inaccurate - monitor warnings)
        """
        if not text:
            return 0  # Empty text = 0 tokens

        try:
            # Use LiteLLM's model-aware token counting
            token_count: int = litellm.token_counter(model=self.model, text=text)  # type: ignore[attr-defined]
            return token_count
        except Exception as e:
            # SECURITY: Log fallback usage for monitoring
            # If you see these warnings frequently, consider:
            # 1. Updating litellm to latest version
            # 2. Adding provider-specific tokenizer for this model
            # 3. Switching to a supported model
            logger.warning(
                f"LiteLLM token counting failed for model {self.model}, using fallback estimate (len/4). "
                f"This may be inaccurate and affect context budget management. Error: {e}",
                extra={
                    "model": self.model,
                    "text_length": len(text),
                    "estimated_tokens": len(text) // 4,
                    "error_type": type(e).__name__,
                },
            )
            return len(text) // 4

    def truncate_response(
        self, content: str, max_tokens: int = MAX_RESPONSE_TOKENS, truncation_message: str | None = None
    ) -> tuple[str, bool]:
        """
        Truncate response to fit within token limit using LiteLLM token counting.

        Args:
            content: Response content to truncate
            max_tokens: Maximum tokens allowed
            truncation_message: Custom message to append when truncated

        Returns:
            Tuple of (truncated_content, was_truncated)
        """
        # Count tokens using LiteLLM
        current_tokens = self.count_tokens(content)

        if current_tokens <= max_tokens:
            return content, False

        # Reserve tokens for truncation message
        if truncation_message is None:
            truncation_message = (
                "\n\n[Response truncated due to length. "
                "Use more specific filters or request detailed format for full results.]"
            )

        message_tokens = self.count_tokens(truncation_message)
        available_tokens = max_tokens - message_tokens

        if available_tokens <= 0:
            logger.warning(
                "Truncation message too long for max_tokens",
                extra={"max_tokens": max_tokens, "message_tokens": message_tokens},
            )
            available_tokens = max(100, max_tokens - 50)

        # Character-based truncation with token counting
        # Estimate characters per token (roughly 4:1 ratio)
        estimated_chars = available_tokens * 4
        truncated_text = content[:estimated_chars]

        # Iteratively adjust until within token limit
        while self.count_tokens(truncated_text) > available_tokens and len(truncated_text) > 100:
            # Reduce by 10% each iteration
            truncated_text = truncated_text[: int(len(truncated_text) * 0.9)]

        final_tokens = self.count_tokens(truncated_text)

        logger.info(
            "Response truncated",
            extra={
                "original_tokens": current_tokens,
                "truncated_tokens": final_tokens,
                "truncation_ratio": final_tokens / current_tokens if current_tokens > 0 else 0,
            },
        )

        return truncated_text + truncation_message, True

    def format_response(
        self, content: str, format_type: Literal["concise", "detailed"] = "concise", max_tokens: int | None = None
    ) -> str:
        """
        Format response according to specified format type.

        Args:
            content: Original response content
            format_type: "concise" or "detailed"
            max_tokens: Override default token limits

        Returns:
            Formatted response
        """
        # Determine token limit based on format
        if max_tokens is None:
            max_tokens = DEFAULT_CONCISE_TOKENS if format_type == "concise" else DEFAULT_DETAILED_TOKENS

        # Truncate if necessary
        formatted_content, was_truncated = self.truncate_response(
            content,
            max_tokens=max_tokens,
            truncation_message=(
                f"\n\n[Response truncated to {format_type} format. " f"Request 'detailed' format for more information.]"
                if format_type == "concise"
                else None
            ),
        )

        return formatted_content

    def extract_high_signal(self, data: dict[str, Any], exclude_fields: list[str] | None = None) -> dict[str, Any]:
        """
        Extract high-signal information from data, removing low-value technical fields.

        Following Anthropic's guidance: "Avoid low-level technical identifiers
        (uuid, mime_type) in favor of human-readable fields (name, file_type)"

        Args:
            data: Dictionary of data
            exclude_fields: Additional fields to exclude

        Returns:
            Dictionary with only high-signal fields
        """
        # Default low-signal fields to exclude
        low_signal_fields = {
            "uuid",
            "guid",
            "mime_type",
            "content_type",
            "created_at_timestamp",
            "updated_at_timestamp",
            "internal_id",
            "trace_id",
            "span_id",
        }

        if exclude_fields:
            low_signal_fields.update(exclude_fields)

        # Filter out low-signal fields
        filtered = {key: value for key, value in data.items() if key not in low_signal_fields}

        return filtered


# Global instance for convenience (uses default model)
# Note: For model-specific counting, create ResponseOptimizer with specific model
_optimizer = ResponseOptimizer()


def count_tokens(text: str, model: str | None = None) -> int:
    """
    Count tokens in text using LiteLLM model-aware counting.

    Args:
        text: Text to count tokens for
        model: Optional model name for accurate counting (uses global default if None)

    Returns:
        Number of tokens
    """
    if model:
        # Use model-specific optimizer for accurate counting
        optimizer = ResponseOptimizer(model=model)
        return optimizer.count_tokens(text)
    else:
        # Use global optimizer with default model
        return _optimizer.count_tokens(text)


def truncate_response(
    content: str, max_tokens: int = MAX_RESPONSE_TOKENS, truncation_message: str | None = None
) -> tuple[str, bool]:
    """Truncate response using global optimizer."""
    return _optimizer.truncate_response(content, max_tokens, truncation_message)


def format_response(
    content: str, format_type: Literal["concise", "detailed"] = "concise", max_tokens: int | None = None
) -> str:
    """Format response using global optimizer."""
    return _optimizer.format_response(content, format_type, max_tokens)


def extract_high_signal(data: dict[str, Any], exclude_fields: list[str] | None = None) -> dict[str, Any]:
    """Extract high-signal information using global optimizer."""
    return _optimizer.extract_high_signal(data, exclude_fields)
