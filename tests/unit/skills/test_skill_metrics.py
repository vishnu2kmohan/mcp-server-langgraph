"""
Unit tests for Skill Execution Metrics

Tests OpenTelemetry metrics for skill execution observability.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.metrics]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_metrics")
class TestSkillMetricsDefinition:
    """Test suite for skill metrics definitions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_metrics_module_exists(self):
        """GIVEN the skills module
        WHEN importing skill metrics
        THEN it should be available
        """
        from mcp_server_langgraph.skills import metrics

        assert metrics is not None

    def test_skill_execution_counter_exists(self):
        """GIVEN skill metrics module
        WHEN checking for execution counter
        THEN it should exist
        """
        from mcp_server_langgraph.skills.metrics import skill_execution_counter

        assert skill_execution_counter is not None

    def test_skill_execution_duration_histogram_exists(self):
        """GIVEN skill metrics module
        WHEN checking for duration histogram
        THEN it should exist
        """
        from mcp_server_langgraph.skills.metrics import skill_execution_duration_histogram

        assert skill_execution_duration_histogram is not None

    def test_skill_execution_error_counter_exists(self):
        """GIVEN skill metrics module
        WHEN checking for error counter
        THEN it should exist
        """
        from mcp_server_langgraph.skills.metrics import skill_execution_error_counter

        assert skill_execution_error_counter is not None

    def test_skill_load_counter_exists(self):
        """GIVEN skill metrics module
        WHEN checking for load counter
        THEN it should exist
        """
        from mcp_server_langgraph.skills.metrics import skill_load_counter

        assert skill_load_counter is not None

    def test_marketplace_fetch_counter_exists(self):
        """GIVEN skill metrics module
        WHEN checking for marketplace fetch counter
        THEN it should exist
        """
        from mcp_server_langgraph.skills.metrics import marketplace_fetch_counter

        assert marketplace_fetch_counter is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_metrics_recording")
class TestSkillMetricsRecording:
    """Test suite for skill metrics recording functions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_skill_execution_success(self):
        """GIVEN a successful skill execution
        WHEN recording metrics
        THEN success counter should be incremented
        """
        from mcp_server_langgraph.skills.metrics import record_skill_execution

        # Should not raise
        record_skill_execution(
            skill_name="web-research",
            script_name="search.py",
            success=True,
            duration_ms=150.5,
        )

    def test_record_skill_execution_failure(self):
        """GIVEN a failed skill execution
        WHEN recording metrics
        THEN error counter should be incremented
        """
        from mcp_server_langgraph.skills.metrics import record_skill_execution

        # Should not raise
        record_skill_execution(
            skill_name="web-research",
            script_name="search.py",
            success=False,
            duration_ms=50.0,
            error_type="timeout",
        )

    def test_record_skill_load(self):
        """GIVEN a skill load event
        WHEN recording metrics
        THEN load counter should be incremented
        """
        from mcp_server_langgraph.skills.metrics import record_skill_load

        # Should not raise
        record_skill_load(
            skill_name="web-research",
            source="local",
            success=True,
        )

    def test_record_marketplace_fetch(self):
        """GIVEN a marketplace fetch event
        WHEN recording metrics
        THEN fetch counter should be incremented
        """
        from mcp_server_langgraph.skills.metrics import record_marketplace_fetch

        # Should not raise
        record_marketplace_fetch(
            marketplace_name="anthropic",
            operation="list_skills",
            success=True,
            cached=False,
        )

    def test_record_marketplace_fetch_cached(self):
        """GIVEN a cached marketplace fetch
        WHEN recording metrics
        THEN fetch counter with cached=True should be incremented
        """
        from mcp_server_langgraph.skills.metrics import record_marketplace_fetch

        # Should not raise
        record_marketplace_fetch(
            marketplace_name="anthropic",
            operation="list_skills",
            success=True,
            cached=True,
        )


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_metrics_labels")
class TestSkillMetricsLabels:
    """Test suite for skill metrics labels"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_execution_metrics_have_skill_label(self):
        """GIVEN skill execution metrics
        WHEN checking labels
        THEN skill_name label should be included
        """
        from mcp_server_langgraph.skills.metrics import SKILL_EXECUTION_LABELS

        assert "skill_name" in SKILL_EXECUTION_LABELS

    def test_execution_metrics_have_script_label(self):
        """GIVEN skill execution metrics
        WHEN checking labels
        THEN script_name label should be included
        """
        from mcp_server_langgraph.skills.metrics import SKILL_EXECUTION_LABELS

        assert "script_name" in SKILL_EXECUTION_LABELS

    def test_execution_metrics_have_success_label(self):
        """GIVEN skill execution metrics
        WHEN checking labels
        THEN success label should be included
        """
        from mcp_server_langgraph.skills.metrics import SKILL_EXECUTION_LABELS

        assert "success" in SKILL_EXECUTION_LABELS

    def test_marketplace_metrics_have_marketplace_label(self):
        """GIVEN marketplace metrics
        WHEN checking labels
        THEN marketplace_name label should be included
        """
        from mcp_server_langgraph.skills.metrics import MARKETPLACE_LABELS

        assert "marketplace_name" in MARKETPLACE_LABELS

    def test_marketplace_metrics_have_cached_label(self):
        """GIVEN marketplace metrics
        WHEN checking labels
        THEN cached label should be included
        """
        from mcp_server_langgraph.skills.metrics import MARKETPLACE_LABELS

        assert "cached" in MARKETPLACE_LABELS
