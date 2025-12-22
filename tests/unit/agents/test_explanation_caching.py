"""
Tests for AI Explanation Caching.

Tests the caching layer for explanation generation:
- Cache key generation
- Cache hit/miss behavior
- TTL expiration
- Cache invalidation
- Redis integration

TDD: These tests are written FIRST before implementation.
"""

from __future__ import annotations

import gc
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.xdist_group(name="explanation_caching")
class TestExplanationCacheKeyGeneration:
    """Tests for cache key generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_cache_key_includes_approval_context(self) -> None:
        """Test that cache key includes approval context."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            generate_explanation_cache_key,
        )

        key = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files matching *.tmp",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        assert key is not None
        assert key.startswith("explanation:")
        # Key should be deterministic
        key2 = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files matching *.tmp",
            confidence=0.65,
            trigger_reason="low_confidence",
        )
        assert key == key2

    def test_different_context_generates_different_keys(self) -> None:
        """Test that different contexts generate different keys."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            generate_explanation_cache_key,
        )

        key1 = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files matching *.tmp",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        key2 = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files matching *.log",  # Different action
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        assert key1 != key2

    def test_similar_confidence_uses_bucketed_key(self) -> None:
        """Test that similar confidence values use same bucket."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            generate_explanation_cache_key,
        )

        # 0.65 and 0.66 should be in same 0.05 bucket (0.65)
        key1 = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        key2 = generate_explanation_cache_key(
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.66,
            trigger_reason="low_confidence",
        )

        assert key1 == key2


@pytest.mark.xdist_group(name="explanation_caching")
class TestExplanationCacheOperations:
    """Tests for cache operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_miss_generates_explanation(self) -> None:
        """Test that cache miss triggers explanation generation."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test explanation"))

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss
        mock_cache.set = AsyncMock()

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        explanation = await orchestrator.generate_explanation_cached(
            approval_id="test-123",
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Should have called LLM (cache miss)
        assert mock_llm.ainvoke.called
        # Should have stored in cache
        assert mock_cache.set.called

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_explanation(self) -> None:
        """Test that cache hit returns cached explanation without LLM call."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock()

        # Create a cached explanation
        cached_explanation = AIExplanation(
            why_uncertain="Cached uncertainty explanation",
            what_could_go_wrong="Cached risk",
        )

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_explanation.model_dump_json())

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        explanation = await orchestrator.generate_explanation_cached(
            approval_id="test-123",
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Should NOT have called LLM (cache hit)
        assert not mock_llm.ainvoke.called
        # Should have used cached explanation
        assert explanation.why_uncertain == "Cached uncertainty explanation"
        assert explanation.cached is True

    @pytest.mark.asyncio
    async def test_cache_set_uses_correct_ttl(self) -> None:
        """Test that cache set uses the configured TTL."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
            EXPLANATION_CACHE_TTL,
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test"))

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        await orchestrator.generate_explanation_cached(
            approval_id="test-123",
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Check TTL was passed
        set_call = mock_cache.set.call_args
        assert set_call is not None
        # TTL should be passed as keyword or positional arg
        if set_call.kwargs.get("ttl"):
            assert set_call.kwargs["ttl"] == EXPLANATION_CACHE_TTL
        elif len(set_call.args) >= 3:
            assert set_call.args[2] == EXPLANATION_CACHE_TTL


@pytest.mark.xdist_group(name="explanation_caching")
class TestExplanationCacheInvalidation:
    """Tests for cache invalidation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalidate_cache_for_approval(self) -> None:
        """Test that we can invalidate cache for a specific approval."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )

        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock(return_value=True)

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=None,
            cache=mock_cache,
        )

        result = await orchestrator.invalidate_explanation_cache(
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

        assert result is True
        assert mock_cache.delete.called

    @pytest.mark.asyncio
    async def test_cache_fallback_on_error(self) -> None:
        """Test graceful fallback when cache fails."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test"))

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_cache.set = AsyncMock(side_effect=Exception("Redis connection failed"))

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        # Should not raise, should fall back to generating explanation
        explanation = await orchestrator.generate_explanation_cached(
            approval_id="test-123",
            agent_name="FileAgent",
            proposed_action="Delete files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        # Should have generated explanation despite cache failure
        assert explanation is not None
        assert mock_llm.ainvoke.called


@pytest.mark.xdist_group(name="explanation_caching")
class TestExplanationCacheMetrics:
    """Tests for cache metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cache_hit_records_metric(self) -> None:
        """Test that cache hit records the correct metric."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        cached = AIExplanation(why_uncertain="Cached", what_could_go_wrong="Cached risk")
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached.model_dump_json())

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=None,
            cache=mock_cache,
        )

        with patch(
            "mcp_server_langgraph.agents.explanation_orchestrator.record_explanation_generation"
        ) as mock_record:
            await orchestrator.generate_explanation_cached(
                approval_id="test-123",
                agent_name="FileAgent",
                proposed_action="Delete files",
                confidence=0.65,
                threshold=0.7,
                trigger_reason="low_confidence",
            )

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args.kwargs
            assert call_kwargs.get("cached") is True

    @pytest.mark.asyncio
    async def test_cache_miss_records_metric(self) -> None:
        """Test that cache miss records the correct metric."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            CachedExplanationOrchestrator,
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test"))

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        orchestrator = CachedExplanationOrchestrator(
            llm_factory=mock_llm,
            cache=mock_cache,
        )

        with patch(
            "mcp_server_langgraph.agents.explanation_orchestrator.record_explanation_generation"
        ) as mock_record:
            await orchestrator.generate_explanation_cached(
                approval_id="test-123",
                agent_name="FileAgent",
                proposed_action="Delete files",
                confidence=0.65,
                threshold=0.7,
                trigger_reason="low_confidence",
            )

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args.kwargs
            assert call_kwargs.get("cached") is False
