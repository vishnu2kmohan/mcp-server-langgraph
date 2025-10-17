"""
Response optimization utilities for token-efficient tool responses.

Implements Anthropic's best practices for writing tools for agents:
- Token counting and truncation
- Response format control (concise vs detailed)
- High-signal information filtering
"""

import tiktoken
from typing import Any, Literal

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

    def __init__(self, model: str = "gpt-4"):
        """
        Initialize response optimizer.

        Args:
            model: Model name for token encoding (default: gpt-4)
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (GPT-4, Claude, Gemini compatible)
            logger.warning(f"Model {model} not found, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def truncate_response(
        self,
        content: str,
        max_tokens: int = MAX_RESPONSE_TOKENS,
        truncation_message: str | None = None
    ) -> tuple[str, bool]:
        """
        Truncate response to fit within token limit.

        Args:
            content: Response content to truncate
            max_tokens: Maximum tokens allowed
            truncation_message: Custom message to append when truncated

        Returns:
            Tuple of (truncated_content, was_truncated)
        """
        tokens = self.encoding.encode(content)

        if len(tokens) <= max_tokens:
            return content, False

        # Reserve tokens for truncation message
        if truncation_message is None:
            truncation_message = (
                "\n\n[Response truncated due to length. "
                "Use more specific filters or request detailed format for full results.]"
            )

        message_tokens = len(self.encoding.encode(truncation_message))
        available_tokens = max_tokens - message_tokens

        if available_tokens <= 0:
            logger.warning(
                "Truncation message too long for max_tokens",
                extra={"max_tokens": max_tokens, "message_tokens": message_tokens}
            )
            available_tokens = max(100, max_tokens - 50)

        # Truncate and decode
        truncated_tokens = tokens[:available_tokens]
        truncated_text = self.encoding.decode(truncated_tokens)

        logger.info(
            "Response truncated",
            extra={
                "original_tokens": len(tokens),
                "truncated_tokens": len(truncated_tokens),
                "truncation_ratio": len(truncated_tokens) / len(tokens)
            }
        )

        return truncated_text + truncation_message, True

    def format_response(
        self,
        content: str,
        format_type: Literal["concise", "detailed"] = "concise",
        max_tokens: int | None = None
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
            max_tokens = (
                DEFAULT_CONCISE_TOKENS if format_type == "concise"
                else DEFAULT_DETAILED_TOKENS
            )

        # Truncate if necessary
        formatted_content, was_truncated = self.truncate_response(
            content,
            max_tokens=max_tokens,
            truncation_message=(
                f"\n\n[Response truncated to {format_type} format. "
                f"Request 'detailed' format for more information.]"
                if format_type == "concise" else None
            )
        )

        return formatted_content

    def extract_high_signal(
        self,
        data: dict[str, Any],
        exclude_fields: list[str] | None = None
    ) -> dict[str, Any]:
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
            "uuid", "guid", "mime_type", "content_type",
            "created_at_timestamp", "updated_at_timestamp",
            "internal_id", "trace_id", "span_id"
        }

        if exclude_fields:
            low_signal_fields.update(exclude_fields)

        # Filter out low-signal fields
        filtered = {
            key: value for key, value in data.items()
            if key not in low_signal_fields
        }

        return filtered


# Global instance for convenience
_optimizer = ResponseOptimizer()


def count_tokens(text: str) -> int:
    """Count tokens in text using global optimizer."""
    return _optimizer.count_tokens(text)


def truncate_response(
    content: str,
    max_tokens: int = MAX_RESPONSE_TOKENS,
    truncation_message: str | None = None
) -> tuple[str, bool]:
    """Truncate response using global optimizer."""
    return _optimizer.truncate_response(content, max_tokens, truncation_message)


def format_response(
    content: str,
    format_type: Literal["concise", "detailed"] = "concise",
    max_tokens: int | None = None
) -> str:
    """Format response using global optimizer."""
    return _optimizer.format_response(content, format_type, max_tokens)


def extract_high_signal(
    data: dict[str, Any],
    exclude_fields: list[str] | None = None
) -> dict[str, Any]:
    """Extract high-signal information using global optimizer."""
    return _optimizer.extract_high_signal(data, exclude_fields)
