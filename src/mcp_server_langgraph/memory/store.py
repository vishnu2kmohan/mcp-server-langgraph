"""Hierarchical MemoryStore with tier-based routing.

Provides unified memory storage interface that routes memories to
appropriate storage backends based on tier:
- WORKING: In-memory dict (ephemeral)
- SESSION: Redis with TTL (temporary)
- DURABLE: PostgreSQL (persistent)
- ARTIFACT: Versioned storage (persistent with versions)

Supports semantic retrieval for relevant memory lookup.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.memory.tiers import MemoryTier


@dataclass
class MemoryEntry:
    """A stored memory entry.

    Attributes:
        id: Unique memory identifier
        content: Memory content
        tier: Storage tier
        scope: Capability scope
        metadata: Optional metadata
    """

    id: str
    content: str
    tier: MemoryTier
    scope: CapabilityScope
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySearchResult:
    """Result from memory semantic search.

    Attributes:
        id: Memory ID
        content: Memory content
        score: Relevance score (0.0 to 1.0)
        tier: Storage tier
    """

    id: str
    content: str
    score: float
    tier: MemoryTier


class MemoryStore:
    """Hierarchical memory store with tier-based routing.

    Routes memory operations to appropriate storage backends based on
    the specified tier. Provides both exact and semantic retrieval.

    Attributes:
        _working_memory: In-memory storage for WORKING tier
        _session_memory: In-memory storage for SESSION tier (would use Redis in production)
        _durable_memory: In-memory storage for DURABLE tier (would use PostgreSQL in production)
        _artifact_memory: In-memory storage for ARTIFACT tier (would use versioned storage in production)
    """

    def __init__(self) -> None:
        """Initialize the memory store with tier-specific storage."""
        # In-memory storage (would be replaced with actual backends in production)
        self._working_memory: dict[str, MemoryEntry] = {}
        self._session_memory: dict[str, MemoryEntry] = {}
        self._durable_memory: dict[str, MemoryEntry] = {}
        self._artifact_memory: dict[str, MemoryEntry] = {}

    async def store(
        self,
        content: str,
        tier: MemoryTier,
        scope: CapabilityScope,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory entry at the specified tier.

        Args:
            content: Memory content to store
            tier: Storage tier
            scope: Capability scope
            metadata: Optional metadata

        Returns:
            Unique memory ID
        """
        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            tier=tier,
            scope=scope,
            metadata=metadata or {},
        )

        # Route to appropriate storage
        storage = self._get_storage_for_tier(tier)
        storage[memory_id] = entry

        return memory_id

    async def retrieve(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID.

        Searches across all tiers to find the memory.

        Args:
            memory_id: Unique memory ID

        Returns:
            MemoryEntry if found, None otherwise
        """
        # Search all tiers
        for storage in [
            self._working_memory,
            self._session_memory,
            self._durable_memory,
            self._artifact_memory,
        ]:
            if memory_id in storage:
                return storage[memory_id]

        return None

    async def get_relevant(
        self,
        query: str,
        scope: CapabilityScope,
        limit: int = 5,
        tiers: list[MemoryTier] | None = None,
    ) -> list[MemorySearchResult]:
        """Get relevant memories using semantic search.

        Performs basic keyword matching for now. In production, this would
        use vector embeddings for semantic similarity.

        Args:
            query: Search query
            scope: Capability scope to search within
            limit: Maximum number of results
            tiers: Optional list of tiers to search (all if None)

        Returns:
            List of MemorySearchResult ordered by relevance
        """
        results: list[MemorySearchResult] = []
        search_tiers = tiers or list(MemoryTier)

        # Simple keyword matching (would use vector search in production)
        query_lower = query.lower()

        for tier in search_tiers:
            storage = self._get_storage_for_tier(tier)
            for entry in storage.values():
                # Check if query terms are in content
                content_lower = entry.content.lower()
                if query_lower in content_lower:
                    # Simple scoring based on position and frequency
                    score = self._calculate_relevance_score(query_lower, content_lower)
                    results.append(
                        MemorySearchResult(
                            id=entry.id,
                            content=entry.content,
                            score=score,
                            tier=entry.tier,
                        )
                    )

        # Sort by score descending and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            memory_id: Unique memory ID

        Returns:
            True if deleted, False if not found
        """
        for storage in [
            self._working_memory,
            self._session_memory,
            self._durable_memory,
            self._artifact_memory,
        ]:
            if memory_id in storage:
                del storage[memory_id]
                return True

        return False

    async def clear_tier(self, tier: MemoryTier) -> int:
        """Clear all memories from a specific tier.

        Args:
            tier: Tier to clear

        Returns:
            Number of entries cleared
        """
        storage = self._get_storage_for_tier(tier)
        count = len(storage)
        storage.clear()
        return count

    def _get_storage_for_tier(self, tier: MemoryTier) -> dict[str, MemoryEntry]:
        """Get the storage dict for a specific tier.

        Args:
            tier: Memory tier

        Returns:
            Storage dict for the tier
        """
        tier_to_storage = {
            MemoryTier.WORKING: self._working_memory,
            MemoryTier.SESSION: self._session_memory,
            MemoryTier.DURABLE: self._durable_memory,
            MemoryTier.ARTIFACT: self._artifact_memory,
        }
        return tier_to_storage[tier]

    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate relevance score for a memory.

        Simple scoring based on query presence. Would use vector
        similarity in production.

        Args:
            query: Search query (lowercase)
            content: Memory content (lowercase)

        Returns:
            Relevance score between 0.0 and 1.0
        """
        if query in content:
            # Higher score for exact match at start
            if content.startswith(query):
                return 1.0
            # Medium score for contains
            return 0.7
        return 0.0
