"""MemoryProgressiveLoader for progressive memory context loading.

Provides progressive loading of memory context:
- Tier-aware retrieval (working, session, durable, artifact)
- Relevance scoring based on query
- Token-aware truncation to fit within limits
- Scope-aware memory retrieval

This enables efficient memory context management for agents.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mcp_server_langgraph.core.scopes import CapabilityScope


@dataclass
class MemoryEntry:
    """A memory entry.

    Attributes:
        id: Unique identifier for the memory
        content: Text content of the memory
        tier: Memory tier (working, session, durable, artifact)
        relevance_score: Optional relevance score (0-1) based on query
        created_at: Optional timestamp when the memory was created
        metadata: Optional metadata about the memory
    """

    id: str
    content: str
    tier: str
    relevance_score: float | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LoadedMemory:
    """Result of progressive memory loading.

    Attributes:
        entries: List of memory entries
        total_tokens: Estimated total tokens in the context
        was_truncated: Whether memories were truncated
        tiers_loaded: List of tiers that were loaded
    """

    entries: list[MemoryEntry]
    total_tokens: int
    was_truncated: bool
    tiers_loaded: list[str] = field(default_factory=list)


class MemoryProgressiveLoader:
    """Progressively loads memory context within token limits.

    Implements tier-aware loading that:
    - Retrieves memories from multiple tiers
    - Scores by relevance to a query
    - Truncates when over token/memory limits
    - Prioritizes by tier and relevance

    Attributes:
        max_memories: Maximum number of memories to load
        max_tokens: Maximum tokens allowed for the context
        tier_priority: Order of tiers to load (first = highest priority)
        scope: Capability scope for memory retrieval
    """

    DEFAULT_MAX_MEMORIES = 20
    DEFAULT_MAX_TOKENS = 4000
    CHARS_PER_TOKEN_ESTIMATE = 4  # Rough estimate: 4 chars per token

    DEFAULT_TIER_PRIORITY = ["working", "session", "durable", "artifact"]

    def __init__(
        self,
        max_memories: int | None = None,
        max_tokens: int | None = None,
        tier_priority: list[str] | None = None,
        scope: CapabilityScope | None = None,
    ) -> None:
        """Initialize the MemoryProgressiveLoader.

        Args:
            max_memories: Maximum memories to load (default: 20)
            max_tokens: Maximum tokens allowed (default: 4000)
            tier_priority: Order of tiers to load (default: working first)
            scope: Capability scope for memory retrieval (default: SESSION)
        """
        self._max_memories = max_memories if max_memories is not None else self.DEFAULT_MAX_MEMORIES
        self._max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        self._tier_priority = tier_priority or self.DEFAULT_TIER_PRIORITY.copy()
        self._scope = scope or CapabilityScope.SESSION

    @property
    def max_memories(self) -> int:
        """Get the maximum memories limit."""
        return self._max_memories

    @property
    def max_tokens(self) -> int:
        """Get the maximum tokens limit."""
        return self._max_tokens

    @property
    def tier_priority(self) -> list[str]:
        """Get the tier priority order."""
        return self._tier_priority

    @property
    def scope(self) -> CapabilityScope:
        """Get the capability scope."""
        return self._scope

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: The text to estimate tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // self.CHARS_PER_TOKEN_ESTIMATE)

    def _retrieve_from_tier(
        self,
        tier: str,
        session_id: str,
    ) -> list[MemoryEntry]:
        """Retrieve memories from a specific tier.

        This is a stub that should be overridden or injected
        with actual storage retrieval logic.

        Args:
            tier: The tier to retrieve from
            session_id: The session ID for scoping

        Returns:
            List of MemoryEntry objects
        """
        # Stub implementation - in production this would
        # query Redis, PostgreSQL, or other storage
        return []

    def _score_relevance(self, entry: MemoryEntry, query: str) -> float:
        """Score a memory's relevance to a query.

        Uses simple keyword matching. In production, this could use
        embeddings for semantic similarity.

        Args:
            entry: The memory entry to score
            query: The query to match against

        Returns:
            Relevance score (0-1)
        """
        if not query:
            return 0.5  # Neutral score when no query

        query_lower = query.lower()
        query_words = set(query_lower.split())
        content_lower = entry.content.lower()

        score = 0.0

        # Check content match
        for word in query_words:
            if word in content_lower:
                score += 0.2
                # Bonus for multiple occurrences
                count = content_lower.count(word)
                if count > 1:
                    score += min(0.1, count * 0.02)

        # Recency bonus if created_at is available
        if entry.created_at is not None:
            # More recent = higher score (simplified)
            score += 0.1

        return min(1.0, score)

    async def load(
        self,
        query: str = "",
        session_id: str = "",
    ) -> LoadedMemory:
        """Load memory context progressively.

        Loads memories from tiers in priority order, scores by relevance,
        and truncates based on limits.

        Args:
            query: Query to use for relevance scoring
            session_id: Session ID for scoping memory retrieval

        Returns:
            LoadedMemory with the loaded entries and metadata
        """
        all_entries: list[MemoryEntry] = []
        tiers_loaded: list[str] = []

        # Retrieve from each tier in priority order
        for tier in self._tier_priority:
            tier_entries = self._retrieve_from_tier(tier, session_id)
            if tier_entries:
                all_entries.extend(tier_entries)
                if tier not in tiers_loaded:
                    tiers_loaded.append(tier)

        if not all_entries:
            return LoadedMemory(
                entries=[],
                total_tokens=0,
                was_truncated=False,
                tiers_loaded=tiers_loaded,
            )

        # Score each entry for relevance
        scored_entries: list[MemoryEntry] = []
        for entry in all_entries:
            score = self._score_relevance(entry, query)
            scored_entry = MemoryEntry(
                id=entry.id,
                content=entry.content,
                tier=entry.tier,
                relevance_score=score,
                created_at=entry.created_at,
                metadata=entry.metadata,
            )
            scored_entries.append(scored_entry)

        # Sort by relevance (highest first)
        scored_entries.sort(
            key=lambda e: e.relevance_score if e.relevance_score is not None else 0,
            reverse=True,
        )

        # Apply limits
        selected_entries: list[MemoryEntry] = []
        total_tokens = 0
        was_truncated = False

        for entry in scored_entries:
            # Check max memories limit
            if len(selected_entries) >= self._max_memories:
                was_truncated = True
                break

            # Check token limit
            entry_tokens = self._estimate_tokens(entry.content)
            # Add overhead for metadata
            entry_tokens += 10

            if total_tokens + entry_tokens > self._max_tokens:
                was_truncated = True
                break

            selected_entries.append(entry)
            total_tokens += entry_tokens

        return LoadedMemory(
            entries=selected_entries,
            total_tokens=total_tokens,
            was_truncated=was_truncated,
            tiers_loaded=tiers_loaded,
        )
