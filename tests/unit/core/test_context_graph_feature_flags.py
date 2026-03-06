"""
Tests for Context Graph Feature Flags (ADR-0101).

TDD RED Phase: These tests verify the feature flag naming and wiring
for context graph decision trace capture and precedent search.

Feature Flags:
- FF_ENABLE_CONTEXT_GRAPH / enable_context_graph
- FF_ENABLE_PRECEDENT_SEARCH / enable_precedent_search
- FF_CONTEXT_GRAPH_ASYNC_PERSISTENCE / context_graph_async_persistence
- FF_CONTEXT_GRAPH_BATCH_SIZE / context_graph_batch_size
- FF_CONTEXT_GRAPH_RETENTION_DAYS / context_graph_retention_days
- FF_CONTEXT_GRAPH_SAMPLING_RATE / context_graph_sampling_rate
- FF_PRECEDENT_SEARCH_MIN_SCORE / precedent_search_min_score
- FF_PRECEDENT_SEARCH_MAX_RESULTS / precedent_search_max_results
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_context_graph_flags")
class TestContextGraphFeatureFlags:
    """Tests for context graph feature flag naming and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flags_has_enable_context_graph(self) -> None:
        """FeatureFlags should have enable_context_graph attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_context_graph")
        assert isinstance(flags.enable_context_graph, bool)

    def test_feature_flags_has_enable_precedent_search(self) -> None:
        """FeatureFlags should have enable_precedent_search attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_precedent_search")
        assert isinstance(flags.enable_precedent_search, bool)

    def test_feature_flags_has_context_graph_async_persistence(self) -> None:
        """FeatureFlags should have context_graph_async_persistence attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "context_graph_async_persistence")
        assert isinstance(flags.context_graph_async_persistence, bool)

    def test_feature_flags_has_context_graph_batch_size(self) -> None:
        """FeatureFlags should have context_graph_batch_size attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "context_graph_batch_size")
        assert isinstance(flags.context_graph_batch_size, int)

    def test_feature_flags_has_context_graph_retention_days(self) -> None:
        """FeatureFlags should have context_graph_retention_days attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "context_graph_retention_days")
        assert isinstance(flags.context_graph_retention_days, int)

    def test_feature_flags_has_context_graph_sampling_rate(self) -> None:
        """FeatureFlags should have context_graph_sampling_rate attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "context_graph_sampling_rate")
        assert isinstance(flags.context_graph_sampling_rate, float)

    def test_feature_flags_has_precedent_search_min_score(self) -> None:
        """FeatureFlags should have precedent_search_min_score attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "precedent_search_min_score")
        assert isinstance(flags.precedent_search_min_score, float)

    def test_feature_flags_has_precedent_search_max_results(self) -> None:
        """FeatureFlags should have precedent_search_max_results attribute."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "precedent_search_max_results")
        assert isinstance(flags.precedent_search_max_results, int)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_context_graph_flags")
class TestContextGraphFeatureFlagsEnvVars:
    """Tests for environment variable wiring of context graph flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_env_var_ff_enable_context_graph(self, monkeypatch) -> None:
        """FF_ENABLE_CONTEXT_GRAPH env var should set flag."""
        monkeypatch.setenv("FF_ENABLE_CONTEXT_GRAPH", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_context_graph is True

    def test_env_var_ff_enable_precedent_search(self, monkeypatch) -> None:
        """FF_ENABLE_PRECEDENT_SEARCH env var should set flag."""
        monkeypatch.setenv("FF_ENABLE_PRECEDENT_SEARCH", "true")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_precedent_search is True

    def test_env_var_ff_context_graph_async_persistence(self, monkeypatch) -> None:
        """FF_CONTEXT_GRAPH_ASYNC_PERSISTENCE env var should set flag."""
        monkeypatch.setenv("FF_CONTEXT_GRAPH_ASYNC_PERSISTENCE", "false")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_async_persistence is False

    def test_env_var_ff_context_graph_batch_size(self, monkeypatch) -> None:
        """FF_CONTEXT_GRAPH_BATCH_SIZE env var should set batch size."""
        monkeypatch.setenv("FF_CONTEXT_GRAPH_BATCH_SIZE", "50")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_batch_size == 50

    def test_env_var_ff_context_graph_retention_days(self, monkeypatch) -> None:
        """FF_CONTEXT_GRAPH_RETENTION_DAYS env var should set retention."""
        monkeypatch.setenv("FF_CONTEXT_GRAPH_RETENTION_DAYS", "365")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_retention_days == 365

    def test_env_var_ff_context_graph_sampling_rate(self, monkeypatch) -> None:
        """FF_CONTEXT_GRAPH_SAMPLING_RATE env var should set rate."""
        monkeypatch.setenv("FF_CONTEXT_GRAPH_SAMPLING_RATE", "0.5")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_sampling_rate == 0.5

    def test_env_var_ff_precedent_search_min_score(self, monkeypatch) -> None:
        """FF_PRECEDENT_SEARCH_MIN_SCORE env var should set min score."""
        monkeypatch.setenv("FF_PRECEDENT_SEARCH_MIN_SCORE", "0.7")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.precedent_search_min_score == 0.7

    def test_env_var_ff_precedent_search_max_results(self, monkeypatch) -> None:
        """FF_PRECEDENT_SEARCH_MAX_RESULTS env var should set max results."""
        monkeypatch.setenv("FF_PRECEDENT_SEARCH_MAX_RESULTS", "20")

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.precedent_search_max_results == 20


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_context_graph_flags")
class TestContextGraphFeatureFlagsDefaults:
    """Tests for default values of context graph flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_context_graph_default_true(self) -> None:
        """enable_context_graph should default to True (promoted after stabilization)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_context_graph is True

    def test_enable_precedent_search_default_true(self) -> None:
        """enable_precedent_search should default to True (promoted after stabilization)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_precedent_search is True

    def test_context_graph_async_persistence_default_true(self) -> None:
        """context_graph_async_persistence should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_async_persistence is True

    def test_context_graph_batch_size_default(self) -> None:
        """context_graph_batch_size should have reasonable default."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_batch_size == 100

    def test_context_graph_retention_days_default(self) -> None:
        """context_graph_retention_days should default to ~7 years."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_retention_days == 2555  # ~7 years

    def test_context_graph_sampling_rate_default(self) -> None:
        """context_graph_sampling_rate should default to 1.0 (all)."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.context_graph_sampling_rate == 1.0

    def test_precedent_search_min_score_default(self) -> None:
        """precedent_search_min_score should default to 0.5."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.precedent_search_min_score == 0.5

    def test_precedent_search_max_results_default(self) -> None:
        """precedent_search_max_results should default to 10."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.precedent_search_max_results == 10
