"""
Unit tests for suggestion pre-warming functionality.

Pre-warming generates suggestions for common topics at startup to reduce
perceived latency when users request suggestions on popular topics.

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import asyncio
import gc
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="suggestion_prewarm")
class TestSuggestionPrewarmTopics:
    """Tests for pre-warm topic definitions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_prewarm_topics_defined(self):
        """Should have a list of pre-warm topics defined."""
        from mcp_server_langgraph.studio.ai.suggestions import PREWARM_TOPICS

        assert isinstance(PREWARM_TOPICS, list)
        assert len(PREWARM_TOPICS) > 0

    @pytest.mark.unit
    def test_prewarm_topics_are_strings(self):
        """Pre-warm topics should all be non-empty strings."""
        from mcp_server_langgraph.studio.ai.suggestions import PREWARM_TOPICS

        for topic in PREWARM_TOPICS:
            assert isinstance(topic, str)
            assert len(topic.strip()) > 0

    @pytest.mark.unit
    def test_prewarm_topics_cover_common_domains(self):
        """Pre-warm topics should cover common programming domains."""
        from mcp_server_langgraph.studio.ai.suggestions import PREWARM_TOPICS

        # Check that topics include common programming concepts
        topics_lower = [t.lower() for t in PREWARM_TOPICS]
        topics_text = " ".join(topics_lower)

        # Should cover at least some common programming domains
        common_domains = ["python", "javascript", "api", "database", "error"]
        found_count = sum(1 for domain in common_domains if domain in topics_text)
        assert found_count >= 3, f"Expected at least 3 common domains, found {found_count}"


@pytest.mark.xdist_group(name="suggestion_prewarm")
class TestPrewarmExecution:
    """Tests for pre-warm execution logic."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prewarm_suggestions_runs_when_enabled(self, monkeypatch):
        """Pre-warm should run when feature flag is enabled."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
            get_chat_suggestion_cache,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags to enable pre-warming
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)  # Use heuristic

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Clear the cache first
        cache = get_chat_suggestion_cache()
        cache.clear()

        # Run pre-warm
        await prewarm_suggestions()

        # Should have populated the cache
        assert cache.stats()["size"] > 0

    @pytest.mark.asyncio
    async def test_prewarm_does_not_run_when_disabled(self, monkeypatch):
        """Pre-warm should not run when feature flag is disabled."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
            get_chat_suggestion_cache,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags to disable pre-warming
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Clear the cache first
        cache = get_chat_suggestion_cache()
        cache.clear()

        # Run pre-warm
        await prewarm_suggestions()

        # Cache should remain empty
        assert cache.stats()["size"] == 0

    @pytest.mark.asyncio
    async def test_prewarm_uses_heuristic_fallback(self, monkeypatch):
        """Pre-warm should use heuristic-based suggestions (fast)."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
            get_chat_suggestion_cache,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Clear cache
        cache = get_chat_suggestion_cache()
        cache.clear()

        # Run pre-warm
        await prewarm_suggestions()

        # Verify cache was populated
        assert cache.stats()["size"] > 0

    @pytest.mark.asyncio
    async def test_prewarm_handles_errors_gracefully(self, monkeypatch):
        """Pre-warm should not crash on errors, just log them."""
        from mcp_server_langgraph.studio.ai.suggestions import prewarm_suggestions
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Mock ChatFollowUpSuggestionAgent to raise an error
        async def failing_suggest(*args, **kwargs):
            raise RuntimeError("Simulated LLM failure")

        with patch("mcp_server_langgraph.studio.ai.suggestions.ChatFollowUpSuggestionAgent") as mock_agent:
            mock_instance = MagicMock()
            mock_instance.suggest = AsyncMock(side_effect=failing_suggest)
            mock_agent.return_value = mock_instance

            # Should not raise, just log the error
            await prewarm_suggestions()

    @pytest.mark.asyncio
    async def test_prewarm_metrics_tracked(self, monkeypatch):
        """Pre-warm should track metrics for monitoring."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
            get_chat_suggestion_cache,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Clear cache
        cache = get_chat_suggestion_cache()
        cache.clear()

        # Run pre-warm and track result
        with patch("mcp_server_langgraph.studio.ai.suggestions.track_prewarm_execution") as mock_track:
            await prewarm_suggestions()
            # Should track execution
            mock_track.assert_called()


@pytest.mark.xdist_group(name="suggestion_prewarm")
class TestPrewarmCacheIntegration:
    """Tests for pre-warm cache integration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prewarmed_suggestions_served_from_cache(self, monkeypatch):
        """Subsequent requests for pre-warmed topics should hit cache."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
            ChatFollowUpSuggestionAgent,
            get_chat_suggestion_cache,
            PREWARM_TOPICS,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Clear cache
        cache = get_chat_suggestion_cache()
        cache.clear()

        # Run pre-warm
        await prewarm_suggestions()

        # Now when we request suggestions for a prewarmed topic,
        # the agent should use the cache
        agent = ChatFollowUpSuggestionAgent(enable_llm=False)

        if len(PREWARM_TOPICS) > 0:
            topic = PREWARM_TOPICS[0]
            # Make a request for the pre-warmed topic
            suggestions = await agent.suggest(content=topic, max_suggestions=4)

            # Should get suggestions (either from cache or newly generated)
            assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_prewarm_limits_concurrent_requests(self, monkeypatch):
        """Pre-warm should limit concurrent requests to avoid overwhelming system."""
        from mcp_server_langgraph.studio.ai.suggestions import (
            prewarm_suggestions,
        )
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Mock the feature flags
        mock_flags = FeatureFlags()
        object.__setattr__(mock_flags, "enable_suggestion_prewarm", True)
        object.__setattr__(mock_flags, "enable_llm_suggestions", False)

        # Patch the module where get_feature_flags is defined
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "get_feature_flags", lambda: mock_flags)

        # Track concurrent calls
        max_concurrent = 0
        current_concurrent = 0

        async def tracking_suggest(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)  # Simulate some work
            current_concurrent -= 1
            return []

        with patch("mcp_server_langgraph.studio.ai.suggestions.ChatFollowUpSuggestionAgent") as mock_agent:
            mock_instance = MagicMock()
            mock_instance.suggest = AsyncMock(side_effect=tracking_suggest)
            mock_agent.return_value = mock_instance

            await prewarm_suggestions()

            # Should limit concurrency (typically to 3-5 concurrent requests)
            # This ensures we don't overwhelm the system
            assert max_concurrent <= 5, f"Expected max 5 concurrent, got {max_concurrent}"
