"""ConversationProgressiveLoader for progressive context loading.

Provides progressive loading of conversation context:
- Token-aware truncation to fit within limits
- Priority for recent messages
- Optional summarization for older context

This enables efficient context management for long conversations.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationMessage:
    """A message in a conversation.

    Attributes:
        role: The role of the message sender (e.g., 'user', 'assistant')
        content: The text content of the message
        timestamp: Optional timestamp when the message was created
    """

    role: str
    content: str
    timestamp: datetime | None = None


@dataclass
class LoadedContext:
    """Result of progressive context loading.

    Attributes:
        messages: List of conversation messages
        total_tokens: Estimated total tokens in the context
        was_truncated: Whether the context was truncated
        summary: Optional summary of truncated content
    """

    messages: list[ConversationMessage]
    total_tokens: int
    was_truncated: bool
    summary: str | None = None


class ConversationProgressiveLoader:
    """Progressively loads conversation context within token limits.

    Implements token-aware loading that:
    - Estimates token usage for messages
    - Prioritizes recent messages
    - Truncates oldest messages when over limit
    - Optionally summarizes truncated content

    Attributes:
        max_tokens: Maximum tokens allowed for the context
    """

    DEFAULT_MAX_TOKENS = 8000
    CHARS_PER_TOKEN_ESTIMATE = 4  # Rough estimate: 4 chars per token

    def __init__(self, max_tokens: int | None = None) -> None:
        """Initialize the ConversationProgressiveLoader.

        Args:
            max_tokens: Maximum tokens allowed (default: 8000)
        """
        self._max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

    @property
    def max_tokens(self) -> int:
        """Get the maximum tokens allowed."""
        return self._max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple character-based estimation.
        In production, this could use tiktoken or model-specific tokenizers.

        Args:
            text: The text to estimate tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // self.CHARS_PER_TOKEN_ESTIMATE)

    async def load(
        self,
        messages: list[ConversationMessage],
    ) -> LoadedContext:
        """Load conversation context progressively.

        Loads as many messages as fit within the token limit,
        prioritizing recent messages.

        Args:
            messages: List of conversation messages (oldest to newest)

        Returns:
            LoadedContext with the loaded messages and metadata
        """
        if not messages:
            return LoadedContext(
                messages=[],
                total_tokens=0,
                was_truncated=False,
            )

        # Work backwards from most recent to oldest
        selected_messages: list[ConversationMessage] = []
        total_tokens = 0
        was_truncated = False

        # Iterate in reverse (newest first)
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens(msg.content)
            # Add overhead for role and formatting
            msg_tokens += self.estimate_tokens(msg.role) + 5

            if total_tokens + msg_tokens <= self._max_tokens:
                selected_messages.insert(0, msg)  # Add to front to maintain order
                total_tokens += msg_tokens
            else:
                was_truncated = True
                # Stop if we can't fit any more
                break

        # Ensure we always include at least the most recent message
        if not selected_messages and messages:
            last_msg = messages[-1]
            msg_tokens = self.estimate_tokens(last_msg.content)
            msg_tokens += self.estimate_tokens(last_msg.role) + 5
            selected_messages = [last_msg]
            total_tokens = msg_tokens
            was_truncated = len(messages) > 1

        return LoadedContext(
            messages=selected_messages,
            total_tokens=total_tokens,
            was_truncated=was_truncated,
        )
