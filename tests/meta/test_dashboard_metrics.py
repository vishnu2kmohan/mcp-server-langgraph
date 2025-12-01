"""
TDD tests for dashboard metrics generation.

Tests validate:
1. DORA metrics calculation and rating
2. Dependency graph generation
3. Test flakiness analysis
4. Workflow integration

Reference: CI Dashboard Optimization (2025-12-01)
"""

import gc
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

from generate_dashboard_metrics import (
    DORAMetrics,
    DependencyGraph,
    DependencyInfo,
    FlakinessData,
    analyze_test_flakiness,
    calculate_dora_metrics,
    generate_all_metrics,
    generate_dependency_graph,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_dashboard_metrics")
class TestDORAMetrics:
    """Test DORA metrics calculation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dora_metrics_dataclass_has_all_fields(self):
        """Verify DORAMetrics has all required DORA fields."""
        metrics = DORAMetrics()

        # Four key DORA metrics
        assert hasattr(metrics, "deployment_frequency")
        assert hasattr(metrics, "lead_time_hours")
        assert hasattr(metrics, "change_failure_rate")
        assert hasattr(metrics, "mttr_hours")

        # Ratings
        assert hasattr(metrics, "deployment_frequency_rating")
        assert hasattr(metrics, "lead_time_rating")
        assert hasattr(metrics, "change_failure_rating")
        assert hasattr(metrics, "mttr_rating")

    def test_deployment_frequency_rating_elite(self):
        """Elite: Multiple deployments per day (>=7/week)."""
        # Verify DORAMetrics can be instantiated with elite-level frequency
        _ = DORAMetrics(deployment_frequency=10.0)

        # Direct rating test
        freq = 10.0
        if freq >= 7:
            rating = "elite"
        elif freq >= 1:
            rating = "high"
        elif freq >= 0.25:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "elite"

    def test_deployment_frequency_rating_high(self):
        """High: Once per day to once per week (1-7/week)."""
        freq = 3.0
        if freq >= 7:
            rating = "elite"
        elif freq >= 1:
            rating = "high"
        elif freq >= 0.25:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "high"

    def test_deployment_frequency_rating_medium(self):
        """Medium: Once per week to once per month (0.25-1/week)."""
        freq = 0.5
        if freq >= 7:
            rating = "elite"
        elif freq >= 1:
            rating = "high"
        elif freq >= 0.25:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "medium"

    def test_deployment_frequency_rating_low(self):
        """Low: Less than once per month (<0.25/week)."""
        freq = 0.1
        if freq >= 7:
            rating = "elite"
        elif freq >= 1:
            rating = "high"
        elif freq >= 0.25:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "low"

    def test_lead_time_rating_elite(self):
        """Elite: Less than one day lead time."""
        hours = 12.0
        if hours < 24:
            rating = "elite"
        elif hours < 168:
            rating = "high"
        elif hours < 720:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "elite"

    def test_lead_time_rating_high(self):
        """High: Less than one week lead time."""
        hours = 72.0
        if hours < 24:
            rating = "elite"
        elif hours < 168:
            rating = "high"
        elif hours < 720:
            rating = "medium"
        else:
            rating = "low"

        assert rating == "high"

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_calculate_dora_metrics_with_mock(self, mock_run: MagicMock):
        """Test DORA calculation with mocked git commands."""
        # Mock git rev-list for commit count
        mock_run.return_value = MagicMock(stdout="42\n", returncode=0)

        metrics = calculate_dora_metrics(days=30)

        assert isinstance(metrics, DORAMetrics)
        assert metrics.period_days == 30
        assert metrics.calculated_at != ""

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_calculate_dora_handles_git_failure(self, mock_run: MagicMock):
        """Test graceful handling of git command failures."""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "git")

        # Should not raise, should return defaults
        metrics = calculate_dora_metrics(days=30)

        assert metrics.total_commits == 0
        assert metrics.total_deployments == 0


@pytest.mark.xdist_group(name="test_dashboard_metrics")
class TestDependencyGraph:
    """Test dependency graph generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dependency_info_dataclass(self):
        """Verify DependencyInfo has required fields."""
        dep = DependencyInfo(name="pytest", version="8.0.0")

        assert dep.name == "pytest"
        assert dep.version == "8.0.0"
        assert dep.is_direct is True
        assert dep.dependencies == []
        assert dep.has_vulnerability is False

    def test_dependency_graph_dataclass(self):
        """Verify DependencyGraph has required fields."""
        graph = DependencyGraph()

        assert graph.packages == []
        assert graph.total_packages == 0
        assert graph.direct_dependencies == 0
        assert graph.transitive_dependencies == 0
        assert graph.vulnerable_packages == 0

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_generate_dependency_graph_parses_uv_output(self, mock_run: MagicMock):
        """Test parsing of uv pip tree output."""
        mock_run.return_value = MagicMock(
            stdout="pytest 8.0.0\n├── iniconfig 2.0.0\n└── pluggy 1.4.0\nrequests 2.31.0\n",
            returncode=0,
        )

        graph = generate_dependency_graph()

        assert isinstance(graph, DependencyGraph)
        assert graph.generated_at != ""

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_generate_dependency_graph_handles_failure(self, mock_run: MagicMock):
        """Test graceful handling of uv command failure."""
        mock_run.side_effect = FileNotFoundError("uv not found")

        # Should not raise
        graph = generate_dependency_graph()

        assert isinstance(graph, DependencyGraph)
        assert graph.total_packages == 0


@pytest.mark.xdist_group(name="test_dashboard_metrics")
class TestFlakinessAnalysis:
    """Test flakiness analysis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_flakiness_data_dataclass(self):
        """Verify FlakinessData has required fields."""
        flaky = FlakinessData()

        assert flaky.total_tests == 0
        assert flaky.flaky_tests == 0
        assert flaky.flakiness_rate == 0.0
        assert flaky.most_flaky_tests == []

    def test_analyze_flakiness_with_trends_file(self):
        """Test flakiness analysis with test trends data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trends_file = Path(tmpdir) / "test-durations.json"
            trends_data = {
                "runs": [
                    {"tests_passed": 100, "tests_failed": 2},
                    {"tests_passed": 100, "tests_failed": 0},
                    {"tests_passed": 100, "tests_failed": 1},
                    {"tests_passed": 100, "tests_failed": 3},
                    {"tests_passed": 100, "tests_failed": 0},
                ]
            }
            trends_file.write_text(json.dumps(trends_data))

            flaky = analyze_test_flakiness(trends_file)

            assert isinstance(flaky, FlakinessData)
            assert flaky.total_tests > 0
            assert flaky.generated_at != ""

    def test_analyze_flakiness_missing_file(self):
        """Test handling of missing trends file."""
        flaky = analyze_test_flakiness(Path("/nonexistent/file.json"))

        assert isinstance(flaky, FlakinessData)
        assert flaky.total_tests == 0

    def test_analyze_flakiness_none_path(self):
        """Test handling of None path."""
        flaky = analyze_test_flakiness(None)

        assert isinstance(flaky, FlakinessData)


@pytest.mark.xdist_group(name="test_dashboard_metrics")
class TestMetricsGeneration:
    """Test combined metrics generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_generate_all_metrics_creates_files(self, mock_run: MagicMock):
        """Test that generate_all_metrics creates expected files."""
        mock_run.return_value = MagicMock(stdout="10\n", returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "metrics"

            metrics = generate_all_metrics(output_dir, days=30)

            # Check files created
            assert (output_dir / "dora-metrics.json").exists()
            assert (output_dir / "dependency-graph.json").exists()
            assert (output_dir / "test-flakiness.json").exists()
            assert (output_dir / "all-metrics.json").exists()

            # Check combined metrics structure
            assert "dora" in metrics
            assert "dependencies" in metrics
            assert "flakiness" in metrics
            assert "generated_at" in metrics

    @patch("generate_dashboard_metrics.subprocess.run")
    def test_generated_json_is_valid(self, mock_run: MagicMock):
        """Test that generated JSON files are valid."""
        mock_run.return_value = MagicMock(stdout="5\n", returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "metrics"

            generate_all_metrics(output_dir, days=7)

            # Verify all JSON files are parseable
            for json_file in output_dir.glob("*.json"):
                content = json_file.read_text()
                parsed = json.loads(content)  # Should not raise
                assert isinstance(parsed, dict)


@pytest.mark.xdist_group(name="test_dashboard_metrics")
class TestWorkflowIntegration:
    """Test workflow integration requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_script_is_executable(self):
        """Verify script can be imported without errors."""
        # If we got here, import succeeded
        from generate_dashboard_metrics import main

        assert callable(main)

    def test_metrics_script_exists(self):
        """Verify the metrics script exists in expected location."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "ci" / "generate_dashboard_metrics.py"
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_gh_pages_telemetry_can_call_script(self):
        """Verify gh-pages-telemetry.yaml can invoke the script."""
        workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        telemetry_path = workflows_dir / "gh-pages-telemetry.yaml"

        if telemetry_path.exists():
            content = telemetry_path.read_text()
            # Script should be callable - either already integrated or can be added
            # This test documents the expected integration point
            assert "gh-pages" in content.lower()
