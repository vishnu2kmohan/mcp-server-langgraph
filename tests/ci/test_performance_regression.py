"""
Tests for Performance Regression Detection

Tests automatic detection of performance regressions in:
- API response times
- Database query times
- Memory usage
- CPU usage

Following TDD practices.
"""

import gc
import json
from unittest.mock import patch

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testperformancebaseline")
class TestPerformanceBaseline:
    """Test performance baseline establishment"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_establish_baseline_from_benchmarks(self):
        """Test establishing performance baseline from benchmark results"""
        # Given: benchmark results
        benchmarks = [
            {"endpoint": "/api/health", "response_time_ms": 50, "memory_mb": 100},
            {"endpoint": "/api/health", "response_time_ms": 55, "memory_mb": 105},
            {"endpoint": "/api/health", "response_time_ms": 52, "memory_mb": 102},
        ]

        # When: establishing baseline
        from scripts.ci.performance_regression import establish_baseline

        baseline = establish_baseline(benchmarks)

        # Then: baseline should be median of results
        assert baseline["response_time_ms"] == pytest.approx(52.0)
        assert baseline["memory_mb"] == pytest.approx(102.0)

    def test_load_historical_baseline(self, tmp_path):
        """Test loading historical baseline from file"""
        # Given: historical baseline file
        baseline_data = {
            "endpoint": "/api/health",
            "response_time_ms": 50.0,
            "memory_mb": 100.0,
            "timestamp": "2025-01-01T12:00:00Z",
        }
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(baseline_data))

        # When: loading baseline
        from scripts.ci.performance_regression import load_baseline

        baseline = load_baseline(baseline_file)

        # Then: should return baseline data
        assert baseline["response_time_ms"] == 50.0


@pytest.mark.xdist_group(name="testregressiondetection")
class TestRegressionDetection:
    """Test regression detection logic"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_response_time_regression(self):
        """Test detecting response time regression"""
        # Given: baseline and current measurements
        baseline = {"response_time_ms": 50.0}
        current = {"response_time_ms": 85.0}  # 70% slower (exceeds 50% threshold)

        # When: detecting regression
        from scripts.ci.performance_regression import detect_regression

        regression = detect_regression(baseline, current, threshold_percent=50)

        # Then: should detect regression
        assert regression["has_regression"] is True
        assert regression["metric"] == "response_time_ms"
        assert regression["degradation_percent"] == pytest.approx(70.0)

    def test_no_regression_within_threshold(self):
        """Test no regression detected when within threshold"""
        # Given: baseline and current within threshold
        baseline = {"response_time_ms": 50.0}
        current = {"response_time_ms": 70.0}  # 40% slower (within 50% threshold)

        # When: detecting regression
        from scripts.ci.performance_regression import detect_regression

        regression = detect_regression(baseline, current, threshold_percent=50)

        # Then: should not detect regression
        assert regression["has_regression"] is False

    def test_detect_memory_regression(self):
        """Test detecting memory usage regression"""
        baseline = {"memory_mb": 100.0}
        current = {"memory_mb": 180.0}  # 80% increase

        from scripts.ci.performance_regression import detect_regression

        regression = detect_regression(baseline, current, threshold_percent=50)

        assert regression["has_regression"] is True
        assert regression["metric"] == "memory_mb"

    def test_detect_multiple_regressions(self):
        """Test detecting multiple regressions"""
        baseline = {
            "response_time_ms": 50.0,
            "memory_mb": 100.0,
            "cpu_percent": 20.0,
        }
        current = {
            "response_time_ms": 85.0,  # 70% regression
            "memory_mb": 180.0,  # 80% regression
            "cpu_percent": 22.0,  # 10% increase (OK)
        }

        from scripts.ci.performance_regression import detect_all_regressions

        regressions = detect_all_regressions(baseline, current, threshold_percent=50)

        assert len(regressions) == 2
        assert any(r["metric"] == "response_time_ms" for r in regressions)
        assert any(r["metric"] == "memory_mb" for r in regressions)


@pytest.mark.xdist_group(name="testperformancebenchmarking")
class TestPerformanceBenchmarking:
    """Test performance benchmarking execution"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("scripts.ci.performance_regression.run_benchmark")
    def test_run_api_benchmarks(self, mock_benchmark):
        """Test running API endpoint benchmarks"""
        # Given: mock benchmark results
        mock_benchmark.return_value = {
            "endpoint": "/api/health",
            "response_time_ms": 52.0,
            "status_code": 200,
        }

        # When: running benchmarks
        from scripts.ci.performance_regression import run_api_benchmarks

        results = run_api_benchmarks(base_url="http://localhost:8000", endpoints=["/api/health"])

        # Then: should return benchmark results
        assert len(results) == 1
        assert results[0]["endpoint"] == "/api/health"

    def test_calculate_percentiles(self):
        """Test percentile calculation for response times"""
        # Given: response time measurements
        measurements = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        # When: calculating percentiles
        from scripts.ci.performance_regression import calculate_percentiles

        percentiles = calculate_percentiles(measurements)

        # Then: should return p50, p95, p99
        assert percentiles["p50"] == pytest.approx(50.0, abs=5)
        assert percentiles["p95"] == pytest.approx(95.0, abs=5)
        assert percentiles["p99"] == pytest.approx(99.0, abs=5)


@pytest.mark.xdist_group(name="testregressionreporting")
class TestRegressionReporting:
    """Test regression reporting and notifications"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_generate_regression_report(self):
        """Test generating regression report"""
        # Given: detected regressions
        regressions = [
            {
                "metric": "response_time_ms",
                "baseline": 50.0,
                "current": 85.0,
                "degradation_percent": 70.0,
                "has_regression": True,
            },
        ]

        # When: generating report
        from scripts.ci.performance_regression import generate_regression_report

        report = generate_regression_report(regressions)

        # Then: report should contain regression details
        assert "Response Time Ms" in report or "response_time_ms" in report
        assert "70" in report
        assert "regression" in report.lower() or "Regression" in report

    def test_create_github_issue_for_regression(self):
        """Test creating GitHub issue for regression"""
        # Given: regression detected
        regression = {
            "metric": "response_time_ms",
            "baseline": 50.0,
            "current": 85.0,
            "degradation_percent": 70.0,
            "endpoint": "/api/health",
            "has_regression": True,
        }

        # When: creating issue
        from scripts.ci.performance_regression import create_regression_issue

        issue_body = create_regression_issue(regression)

        # Then: issue body should contain details
        assert "Response Time Ms" in issue_body or "response_time_ms" in issue_body
        assert "/api/health" in issue_body
        assert "70" in issue_body


@pytest.mark.xdist_group(name="testbaselineupdate")
class TestBaselineUpdate:
    """Test baseline update logic"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_update_baseline_after_improvement(self):
        """Test updating baseline after performance improvement"""
        # Given: improved performance
        baseline = {"response_time_ms": 50.0}
        current = {"response_time_ms": 35.0}  # 30% faster

        # When: updating baseline
        from scripts.ci.performance_regression import should_update_baseline

        should_update = should_update_baseline(baseline, current, improvement_threshold=20)

        # Then: should recommend baseline update
        assert should_update is True

    def test_no_baseline_update_for_minor_changes(self):
        """Test not updating baseline for minor changes"""
        baseline = {"response_time_ms": 50.0}
        current = {"response_time_ms": 48.0}  # 4% faster (minor)

        from scripts.ci.performance_regression import should_update_baseline

        should_update = should_update_baseline(baseline, current, improvement_threshold=20)

        assert should_update is False

    def test_save_updated_baseline(self, tmp_path):
        """Test saving updated baseline to file"""
        # Given: new baseline
        baseline = {
            "response_time_ms": 35.0,
            "memory_mb": 80.0,
            "timestamp": "2025-01-01T12:00:00Z",
        }

        # When: saving baseline
        from scripts.ci.performance_regression import save_baseline

        baseline_file = tmp_path / "baseline.json"
        save_baseline(baseline, baseline_file)

        # Then: file should contain baseline
        assert baseline_file.exists()
        saved = json.loads(baseline_file.read_text())
        assert saved["response_time_ms"] == 35.0
