"""Memory tier definitions for hierarchical memory architecture.

Defines the four-tier memory hierarchy:
- WORKING: Ephemeral, in-memory only (current task context)
- SESSION: Temporary with TTL (Redis-backed for session persistence)
- DURABLE: Persistent storage (PostgreSQL for long-term retention)
- ARTIFACT: Versioned artifacts (code, files, structured outputs)

Each tier has different persistence characteristics and TTL behavior.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from enum import StrEnum


class MemoryTier(StrEnum):
    """Memory tier classification for hierarchical storage.

    Tiers are ordered by persistence duration:
    - WORKING: Ephemeral (task lifetime only)
    - SESSION: Temporary (session lifetime with TTL)
    - DURABLE: Persistent (no expiry)
    - ARTIFACT: Versioned (no expiry, version controlled)
    """

    WORKING = "working"
    SESSION = "session"
    DURABLE = "durable"
    ARTIFACT = "artifact"


# Tier persistence characteristics
_TIER_PERSISTENCE: dict[MemoryTier, str] = {
    MemoryTier.WORKING: "ephemeral",
    MemoryTier.SESSION: "temporary",
    MemoryTier.DURABLE: "persistent",
    MemoryTier.ARTIFACT: "versioned",
}

# Default TTL in seconds (None = no expiry)
_TIER_DEFAULT_TTL: dict[MemoryTier, int | None] = {
    MemoryTier.WORKING: 0,  # No TTL, in-memory only
    MemoryTier.SESSION: 3600,  # 1 hour default
    MemoryTier.DURABLE: None,  # No expiry
    MemoryTier.ARTIFACT: None,  # No expiry
}


def get_tier_persistence(tier: MemoryTier) -> str:
    """Get the persistence type for a memory tier.

    Args:
        tier: MemoryTier to query

    Returns:
        Persistence type: "ephemeral", "temporary", "persistent", or "versioned"
    """
    return _TIER_PERSISTENCE[tier]


def get_tier_default_ttl(tier: MemoryTier) -> int | None:
    """Get the default TTL for a memory tier.

    Args:
        tier: MemoryTier to query

    Returns:
        Default TTL in seconds, or None for no expiry
    """
    return _TIER_DEFAULT_TTL[tier]
