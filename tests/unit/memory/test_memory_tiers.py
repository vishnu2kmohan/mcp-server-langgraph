"""Tests for MemoryTier enum.

TDD: These tests define the contract for memory tier classification
in the hierarchical memory architecture.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestMemoryTierBasic:
    """Tests for MemoryTier enum basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_tier_exists(self) -> None:
        """Test MemoryTier enum exists."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert MemoryTier is not None

    def test_memory_tier_has_four_levels(self) -> None:
        """Test MemoryTier has four levels."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        members = list(MemoryTier)
        assert len(members) == 4

    def test_memory_tier_has_working(self) -> None:
        """Test MemoryTier has WORKING level."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert hasattr(MemoryTier, "WORKING")
        assert MemoryTier.WORKING.value == "working"

    def test_memory_tier_has_session(self) -> None:
        """Test MemoryTier has SESSION level."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert hasattr(MemoryTier, "SESSION")
        assert MemoryTier.SESSION.value == "session"

    def test_memory_tier_has_durable(self) -> None:
        """Test MemoryTier has DURABLE level."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert hasattr(MemoryTier, "DURABLE")
        assert MemoryTier.DURABLE.value == "durable"

    def test_memory_tier_has_artifact(self) -> None:
        """Test MemoryTier has ARTIFACT level."""
        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert hasattr(MemoryTier, "ARTIFACT")
        assert MemoryTier.ARTIFACT.value == "artifact"

    def test_memory_tier_is_str_enum(self) -> None:
        """Test MemoryTier is a StrEnum."""
        from enum import StrEnum

        from mcp_server_langgraph.memory.tiers import MemoryTier

        assert issubclass(MemoryTier, StrEnum)


@pytest.mark.unit
class TestMemoryTierProperties:
    """Tests for MemoryTier tier properties."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_working_tier_is_ephemeral(self) -> None:
        """Test WORKING tier is ephemeral (in-memory only)."""
        from mcp_server_langgraph.memory.tiers import MemoryTier, get_tier_persistence

        persistence = get_tier_persistence(MemoryTier.WORKING)
        assert persistence == "ephemeral"

    def test_session_tier_is_temporary(self) -> None:
        """Test SESSION tier is temporary (Redis with TTL)."""
        from mcp_server_langgraph.memory.tiers import MemoryTier, get_tier_persistence

        persistence = get_tier_persistence(MemoryTier.SESSION)
        assert persistence == "temporary"

    def test_durable_tier_is_persistent(self) -> None:
        """Test DURABLE tier is persistent (PostgreSQL)."""
        from mcp_server_langgraph.memory.tiers import MemoryTier, get_tier_persistence

        persistence = get_tier_persistence(MemoryTier.DURABLE)
        assert persistence == "persistent"

    def test_artifact_tier_is_versioned(self) -> None:
        """Test ARTIFACT tier is versioned."""
        from mcp_server_langgraph.memory.tiers import MemoryTier, get_tier_persistence

        persistence = get_tier_persistence(MemoryTier.ARTIFACT)
        assert persistence == "versioned"

    def test_tier_default_ttl(self) -> None:
        """Test tiers have appropriate default TTLs."""
        from mcp_server_langgraph.memory.tiers import MemoryTier, get_tier_default_ttl

        # Working is ephemeral - very short TTL
        assert get_tier_default_ttl(MemoryTier.WORKING) == 0  # No TTL, in-memory

        # Session has TTL (e.g., 1 hour)
        assert get_tier_default_ttl(MemoryTier.SESSION) > 0

        # Durable and Artifact are permanent
        assert get_tier_default_ttl(MemoryTier.DURABLE) is None  # No expiry
        assert get_tier_default_ttl(MemoryTier.ARTIFACT) is None  # No expiry
