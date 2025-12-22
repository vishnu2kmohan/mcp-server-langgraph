"""
Context filter implementations for Handoff pattern (ADR-0081)

This module provides context filtering utilities for controlling what
conversation history is passed when transferring control between agents.

Usage:
    from mcp_server_langgraph.agents.context_filter import (
        KeepLastNFilter,
        RemoveToolCallsFilter,
        SummarizeHistoryFilter,
        ChainedFilter,
    )

    # Keep only last 5 messages
    filter_obj = KeepLastNFilter(n=5)
    filtered = filter_obj.filter(messages)

    # Chain multiple filters
    chained = ChainedFilter(filters=[
        RemoveToolCallsFilter(),
        KeepLastNFilter(n=10),
    ])
    filtered = chained.filter(messages)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ContextFilter(ABC):
    """Base class for context filters.

    Context filters transform message lists before passing them
    to the target agent during a handoff.
    """

    @abstractmethod
    def filter(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter the message list.

        Args:
            messages: List of message dictionaries

        Returns:
            Filtered list of messages
        """
        ...


@dataclass
class KeepLastNFilter(ContextFilter):
    """Keep only the last N messages.

    Attributes:
        n: Number of messages to keep from the end
    """

    n: int

    def filter(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only the last N messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Last N messages
        """
        if len(messages) <= self.n:
            return messages.copy()
        return messages[-self.n :]


@dataclass
class RemoveToolCallsFilter(ContextFilter):
    """Remove tool call and tool result messages.

    This filter removes:
    - Messages with role="tool"
    - Messages containing tool_calls
    """

    def filter(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove tool-related messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Messages without tool calls or tool results
        """
        result = []
        for msg in messages:
            # Skip tool result messages
            if msg.get("role") == "tool":
                continue
            # Skip messages with tool_calls
            if "tool_calls" in msg:
                continue
            result.append(msg.copy())
        return result


@dataclass
class SummarizeHistoryFilter(ContextFilter):
    """Summarize older messages and keep recent ones.

    Creates a summary message for older history, then appends
    the most recent messages.

    Attributes:
        keep_recent: Number of recent messages to preserve
        summary_template: Template for summary message with {count} placeholder
    """

    keep_recent: int = 5
    summary_template: str = "Previous conversation: {count} messages exchanged"

    def filter(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create summary of older messages plus recent ones.

        Args:
            messages: List of message dictionaries

        Returns:
            Summary message followed by recent messages
        """
        if len(messages) <= self.keep_recent:
            return messages.copy()

        # Count messages to summarize
        older_count = len(messages) - self.keep_recent

        # Create summary message
        summary_content = self.summary_template.format(count=older_count)
        summary_msg: dict[str, Any] = {
            "role": "system",
            "content": summary_content,
        }

        # Get recent messages
        recent = messages[-self.keep_recent :]

        return [summary_msg, *recent]


@dataclass
class ChainedFilter(ContextFilter):
    """Chain multiple filters together.

    Applies filters in order, passing output of each to the next.

    Attributes:
        filters: List of filters to apply in order
    """

    filters: list[ContextFilter] = field(default_factory=list)

    def filter(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply all filters in sequence.

        Args:
            messages: List of message dictionaries

        Returns:
            Messages after all filters have been applied
        """
        result = messages
        for filter_obj in self.filters:
            result = filter_obj.filter(result)
        return result


__all__ = [
    "ChainedFilter",
    "ContextFilter",
    "KeepLastNFilter",
    "RemoveToolCallsFilter",
    "SummarizeHistoryFilter",
]
