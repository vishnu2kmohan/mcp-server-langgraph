"""
Dynamic Context Splitting.

Phase 7 of the Multi-Agent Orchestrator Enhancement Plan.

Splits large tasks that exceed model context windows into
smaller chunks at semantic boundaries (paragraphs, sections).

Usage:
    from mcp_server_langgraph.agents.context_splitter import (
        ContextSplitter,
        TaskChunk,
    )

    splitter = ContextSplitter()

    if splitter.needs_split(task, "claude-opus-4-5-20251101"):
        chunks = splitter.split_task(task, "claude-opus-4-5-20251101")
        for chunk in chunks:
            process(chunk)
    else:
        process_single(task)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp_server_langgraph.agents.model_registry import (
    ModelRegistry,
    get_default_registry,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    pass


@dataclass
class TaskChunk:
    """A chunk of a split task.

    Represents one segment of a task that was too large to
    fit in a single model context window.

    Attributes:
        content: The text content of this chunk
        index: Zero-based index of this chunk
        total: Total number of chunks in the split
        token_count: Estimated token count for this chunk
        boundary_type: Type of boundary used for split (paragraph, section)
    """

    content: str
    index: int
    total: int
    token_count: int | None = None
    boundary_type: str | None = None


class ContextSplitter:
    """Splits large tasks at semantic boundaries.

    Uses ModelRegistry to determine context limits and splits
    tasks at paragraph or section boundaries when they exceed
    the configurable threshold.

    Usage:
        splitter = ContextSplitter()

        chunks = splitter.split_task(
            "Very long task...",
            "claude-opus-4-5-20251101"
        )
        # Returns list of TaskChunk
    """

    # Approximate chars per token (conservative estimate)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        split_threshold: float | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        """Initialize ContextSplitter.

        Args:
            split_threshold: Percentage of effective limit to use as split target.
                Defaults to feature_flags.context_split_threshold.
            model_registry: ModelRegistry for context limit lookup.
                Defaults to the global registry.
        """
        self.split_threshold = split_threshold or feature_flags.context_split_threshold
        self.model_registry = model_registry or get_default_registry()

    def split_task(self, task: str, model: str) -> list[TaskChunk]:
        """Split a task into chunks that fit in model context.

        Args:
            task: The task text to split
            model: Model identifier for context limit lookup

        Returns:
            List of TaskChunk. Returns single chunk if no split needed.
        """
        if not self.needs_split(task, model):
            return [
                TaskChunk(
                    content=task,
                    index=0,
                    total=1,
                    token_count=self.count_tokens(task),
                )
            ]

        # Find semantic boundaries
        boundaries = self.find_boundaries(task)

        # Split at boundaries
        target_tokens = self.get_split_target(model)
        chunks = self._split_at_boundaries(task, boundaries, target_tokens)

        return chunks

    def needs_split(self, task: str, model: str) -> bool:
        """Check if task needs to be split.

        Args:
            task: The task text
            model: Model identifier

        Returns:
            True if task tokens exceed split threshold
        """
        task_tokens = self.count_tokens(task)
        split_target = self.get_split_target(model)
        return task_tokens > split_target

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses simple character-based heuristic.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        return len(text) // self.CHARS_PER_TOKEN

    def find_boundaries(self, text: str) -> list[int]:
        """Find semantic boundaries in text.

        Detects:
        - Paragraph breaks (double newlines)
        - Section headers (markdown # headers)
        - Sentence ends followed by newlines

        Args:
            text: Text to analyze

        Returns:
            List of character positions where boundaries occur
        """
        boundaries: list[int] = []

        # Find paragraph breaks (double newlines)
        for match in re.finditer(r"\n\n+", text):
            boundaries.append(match.end())

        # Find markdown section headers
        for match in re.finditer(r"\n#{1,6}\s+", text):
            boundaries.append(match.start())

        # Remove duplicates and sort
        boundaries = sorted(set(boundaries))

        return boundaries

    def get_effective_limit(self, model: str) -> int:
        """Get effective context limit for model.

        Args:
            model: Model identifier

        Returns:
            Effective context limit in tokens
        """
        # ModelRegistry.get() always returns ModelCapabilities with defaults
        caps = self.model_registry.get(model)
        if caps.effective_limit is not None:
            return caps.effective_limit
        # Fallback to 65% of advertised limit
        return int(caps.context_limit * 0.65)

    def get_split_target(self, model: str) -> int:
        """Get target token count for each chunk.

        Applies split threshold to effective limit.

        Args:
            model: Model identifier

        Returns:
            Target tokens per chunk
        """
        effective = self.get_effective_limit(model)
        return int(effective * self.split_threshold)

    def _split_at_boundaries(
        self,
        text: str,
        boundaries: list[int],
        target_tokens: int,
    ) -> list[TaskChunk]:
        """Split text at boundaries to fit target token count.

        Args:
            text: Text to split
            boundaries: List of boundary positions
            target_tokens: Target tokens per chunk

        Returns:
            List of TaskChunk
        """
        if not boundaries:
            # No boundaries found, return as single chunk
            return [
                TaskChunk(
                    content=text,
                    index=0,
                    total=1,
                    token_count=self.count_tokens(text),
                )
            ]

        chunks: list[TaskChunk] = []
        chunk_start = 0

        for boundary in boundaries:
            chunk_text = text[chunk_start:boundary]
            chunk_tokens = self.count_tokens(chunk_text)

            if chunk_tokens >= target_tokens and chunk_text.strip():
                # This chunk is big enough, add it
                chunks.append(
                    TaskChunk(
                        content=chunk_text.strip(),
                        index=len(chunks),
                        total=0,  # Will update later
                        token_count=chunk_tokens,
                        boundary_type="paragraph",
                    )
                )
                chunk_start = boundary

        # Add remaining text as final chunk
        remaining = text[chunk_start:].strip()
        if remaining:
            chunks.append(
                TaskChunk(
                    content=remaining,
                    index=len(chunks),
                    total=0,
                    token_count=self.count_tokens(remaining),
                    boundary_type="paragraph",
                )
            )

        # If no chunks created, return original as single chunk
        if not chunks:
            chunks = [
                TaskChunk(
                    content=text,
                    index=0,
                    total=1,
                    token_count=self.count_tokens(text),
                )
            ]

        # Update total count in all chunks
        for chunk in chunks:
            chunk.total = len(chunks)

        return chunks
