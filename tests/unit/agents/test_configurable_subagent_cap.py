"""
Tests for configurable subagent cap.

Phase 4 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Tests:
1. Feature flag max_subagents exists
2. scale_effort uses feature flag limit
3. Default limit is 10
4. Custom limit is respected
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="configurable_subagent_cap")
class TestMaxSubagentsFeatureFlag:
    """Test max_subagents feature flag."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flag_max_subagents_exists(self) -> None:
        """Feature flags should include max_subagents."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "max_subagents")

    def test_feature_flag_max_subagents_default_is_10(self) -> None:
        """Default max_subagents should be 10."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.max_subagents == 10

    def test_feature_flag_max_subagents_has_validation(self) -> None:
        """max_subagents should have ge=1, le=50 validation."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Test with valid value
        ff = FeatureFlags(max_subagents=25)
        assert ff.max_subagents == 25

        # Test with edge values
        ff_min = FeatureFlags(max_subagents=1)
        assert ff_min.max_subagents == 1

        ff_max = FeatureFlags(max_subagents=50)
        assert ff_max.max_subagents == 50


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="scale_effort_cap")
class TestScaleEffortCap:
    """Test scale_effort uses configurable cap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scale_effort_respects_default_limit(self) -> None:
        """scale_effort should respect default max_subagents limit of 10."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        # Very complex task that would normally exceed 10
        complex_task = " ".join(
            [
                "comprehensive",
                "thorough",
                "detailed",
                "analyze",
                "research",
                "investigate",
                "compare",
                "multiple",
            ]
            * 5
        )  # 40 complex keywords + lots of words

        result = orchestrator.scale_effort(complex_task)

        # Should be capped at 10 (default)
        assert result <= 10

    def test_scale_effort_with_custom_limit(self) -> None:
        """scale_effort should use custom max_subagents from feature flags."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        # Very complex task
        complex_task = " ".join(
            [
                "comprehensive",
                "thorough",
                "detailed",
                "analyze",
                "research",
                "investigate",
                "compare",
                "multiple",
            ]
            * 5
        )

        with patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_flags:
            mock_flags.max_subagents = 20
            mock_flags.enable_multi_agent_orchestration = True
            result = orchestrator.scale_effort(complex_task)

        # Should be capped at 20 (custom)
        assert result <= 20

    def test_scale_effort_with_lower_limit(self) -> None:
        """scale_effort should respect lower custom limit."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        # Complex task
        complex_task = "comprehensive thorough detailed analyze research"

        with patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_flags:
            mock_flags.max_subagents = 3
            mock_flags.enable_multi_agent_orchestration = True
            result = orchestrator.scale_effort(complex_task)

        # Should be capped at 3
        assert result <= 3

    def test_scale_effort_minimum_is_always_1(self) -> None:
        """scale_effort should always return at least 1."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        # Simple task
        result = orchestrator.scale_effort("hello")

        assert result >= 1
