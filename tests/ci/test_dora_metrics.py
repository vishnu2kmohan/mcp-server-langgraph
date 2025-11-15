"""
Tests for DORA Metrics Tracking

Tests the four key DORA metrics:
1. Deployment Frequency
2. Lead Time for Changes
3. Mean Time to Recovery (MTTR)
4. Change Failure Rate

Following TDD practices - tests written before implementation.
"""

import gc
import json
from unittest.mock import patch

import pytest


@pytest.mark.xdist_group(name="testdorametricscalculation")
class TestDORAMetricsCalculation:
    """Test DORA metrics calculation logic"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_calculate_deployment_frequency_daily(self):
        """Test deployment frequency calculation for daily deployments"""
        # Given: deployments in the last 30 days
        deployments = [
            {"timestamp": "2025-01-01T10:00:00Z", "environment": "production"},
            {"timestamp": "2025-01-02T10:00:00Z", "environment": "production"},
            {"timestamp": "2025-01-03T10:00:00Z", "environment": "production"},
        ]

        # When: calculating deployment frequency
        from scripts.ci.dora_metrics import calculate_deployment_frequency

        frequency = calculate_deployment_frequency(deployments, days=3)

        # Then: should return 1 deployment per day
        assert frequency == 1.0

    def test_calculate_deployment_frequency_multiple_per_day(self):
        """Test deployment frequency with multiple deployments per day"""
        deployments = [
            {"timestamp": "2025-01-01T10:00:00Z", "environment": "production"},
            {"timestamp": "2025-01-01T14:00:00Z", "environment": "production"},
            {"timestamp": "2025-01-01T18:00:00Z", "environment": "production"},
        ]

        from scripts.ci.dora_metrics import calculate_deployment_frequency

        frequency = calculate_deployment_frequency(deployments, days=1)

        assert frequency == 3.0

    def test_calculate_lead_time_from_commit_to_deploy(self):
        """Test lead time calculation from first commit to deployment"""
        # Given: commits and deployment
        commits = [
            {"sha": "abc123", "timestamp": "2025-01-01T10:00:00Z"},
            {"sha": "def456", "timestamp": "2025-01-01T11:00:00Z"},
        ]
        deployment = {"timestamp": "2025-01-01T14:00:00Z", "commits": ["abc123", "def456"]}

        # When: calculating lead time
        from scripts.ci.dora_metrics import calculate_lead_time

        lead_time_hours = calculate_lead_time(commits, deployment)

        # Then: lead time should be from first commit to deployment (4 hours)
        assert lead_time_hours == 4.0

    def test_calculate_mttr_from_incident_to_recovery(self):
        """Test MTTR calculation from incident detection to recovery"""
        # Given: incident and recovery deployment
        incident = {
            "detected_at": "2025-01-01T10:00:00Z",
            "severity": "high",
        }
        recovery_deployment = {
            "timestamp": "2025-01-01T12:30:00Z",
            "type": "hotfix",
        }

        # When: calculating MTTR
        from scripts.ci.dora_metrics import calculate_mttr

        mttr_hours = calculate_mttr(incident, recovery_deployment)

        # Then: MTTR should be 2.5 hours
        assert mttr_hours == 2.5

    def test_calculate_change_failure_rate(self):
        """Test change failure rate calculation"""
        # Given: deployments with some failures
        deployments = [
            {"status": "success", "timestamp": "2025-01-01T10:00:00Z"},
            {"status": "failed", "timestamp": "2025-01-01T11:00:00Z"},
            {"status": "success", "timestamp": "2025-01-01T12:00:00Z"},
            {"status": "failed", "timestamp": "2025-01-01T13:00:00Z"},
            {"status": "success", "timestamp": "2025-01-01T14:00:00Z"},
        ]

        # When: calculating change failure rate
        from scripts.ci.dora_metrics import calculate_change_failure_rate

        failure_rate = calculate_change_failure_rate(deployments)

        # Then: failure rate should be 40% (2 out of 5)
        assert failure_rate == 40.0

    def test_calculate_change_failure_rate_all_success(self):
        """Test change failure rate with all successful deployments"""
        deployments = [
            {"status": "success", "timestamp": "2025-01-01T10:00:00Z"},
            {"status": "success", "timestamp": "2025-01-01T11:00:00Z"},
        ]

        from scripts.ci.dora_metrics import calculate_change_failure_rate

        failure_rate = calculate_change_failure_rate(deployments)

        assert failure_rate == 0.0

    def test_classify_dora_performance_elite(self):
        """Test DORA performance classification - Elite"""
        # Given: elite metrics
        metrics = {
            "deployment_frequency_per_day": 3.0,  # On-demand (multiple per day)
            "lead_time_hours": 0.5,  # Less than one hour
            "mttr_hours": 0.25,  # Less than one hour
            "change_failure_rate": 5.0,  # 0-15%
        }

        # When: classifying performance
        from scripts.ci.dora_metrics import classify_dora_performance

        classification = classify_dora_performance(metrics)

        # Then: should be classified as Elite
        assert classification == "Elite"

    def test_classify_dora_performance_high(self):
        """Test DORA performance classification - High"""
        metrics = {
            "deployment_frequency_per_day": 0.5,  # Between once per day and once per week
            "lead_time_hours": 12.0,  # Between one day and one week
            "mttr_hours": 12.0,  # Less than one day
            "change_failure_rate": 10.0,  # 0-15%
        }

        from scripts.ci.dora_metrics import classify_dora_performance

        classification = classify_dora_performance(metrics)

        assert classification == "High"

    def test_classify_dora_performance_medium(self):
        """Test DORA performance classification - Medium"""
        metrics = {
            "deployment_frequency_per_day": 0.1,  # Between once per week and once per month
            "lead_time_hours": 200.0,  # Between one week and one month
            "mttr_hours": 100.0,  # Less than one week
            "change_failure_rate": 20.0,  # 16-30%
        }

        from scripts.ci.dora_metrics import classify_dora_performance

        classification = classify_dora_performance(metrics)

        assert classification == "Medium"


@pytest.mark.xdist_group(name="testdorametricscollection")
class TestDORAMetricsCollection:
    """Test DORA metrics data collection from GitHub API"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("scripts.ci.dora_metrics.GitHubClient")
    def test_collect_deployment_data_from_github(self, mock_github):
        """Test collecting deployment data from GitHub deployments API"""
        # Given: mock GitHub API responses
        mock_github.return_value.get_deployments.return_value = [
            {
                "id": 1,
                "environment": "production",
                "created_at": "2025-01-01T10:00:00Z",
                "statuses": [{"state": "success"}],
            },
        ]

        # When: collecting deployment data
        from scripts.ci.dora_metrics import collect_deployment_data

        deployments = collect_deployment_data("owner/repo", days=30)

        # Then: should return parsed deployment data
        assert len(deployments) == 1
        assert deployments[0]["environment"] == "production"
        assert deployments[0]["status"] == "success"

    @patch("scripts.ci.dora_metrics.GitHubClient")
    def test_collect_commit_data_from_github(self, mock_github):
        """Test collecting commit data from GitHub API"""
        mock_github.return_value.get_commits.return_value = [
            {
                "sha": "abc123",
                "commit": {
                    "author": {"date": "2025-01-01T10:00:00Z"},
                    "message": "feat: add new feature",
                },
            },
        ]

        from scripts.ci.dora_metrics import collect_commit_data

        commits = collect_commit_data("owner/repo", since="2025-01-01")

        assert len(commits) == 1
        assert commits[0]["sha"] == "abc123"


@pytest.mark.xdist_group(name="testdorametricsstorage")
class TestDORAMetricsStorage:
    """Test DORA metrics storage and retrieval"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_save_metrics_to_json_file(self, tmp_path):
        """Test saving DORA metrics to JSON file"""
        # Given: calculated metrics
        metrics = {
            "timestamp": "2025-01-01T12:00:00Z",
            "deployment_frequency_per_day": 2.5,
            "lead_time_hours": 1.5,
            "mttr_hours": 0.5,
            "change_failure_rate": 5.0,
            "classification": "Elite",
        }

        # When: saving to file
        from scripts.ci.dora_metrics import save_metrics

        output_file = tmp_path / "dora-metrics.json"
        save_metrics(metrics, output_file)

        # Then: file should contain metrics (saves as array)
        assert output_file.exists()
        saved_data = json.loads(output_file.read_text())
        assert isinstance(saved_data, list)
        assert saved_data[-1]["classification"] == "Elite"

    def test_load_historical_metrics(self, tmp_path):
        """Test loading historical metrics for trending"""
        # Given: historical metrics file
        historical_data = [
            {"timestamp": "2025-01-01", "classification": "High"},
            {"timestamp": "2025-01-02", "classification": "Elite"},
        ]
        metrics_file = tmp_path / "dora-history.json"
        metrics_file.write_text(json.dumps(historical_data))

        # When: loading historical data
        from scripts.ci.dora_metrics import load_historical_metrics

        history = load_historical_metrics(metrics_file)

        # Then: should return historical data
        assert len(history) == 2
        assert history[1]["classification"] == "Elite"


@pytest.mark.xdist_group(name="testdorametricsreporting")
class TestDORAMetricsReporting:
    """Test DORA metrics reporting and visualization"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_generate_markdown_report(self):
        """Test generating markdown report for metrics"""
        # Given: calculated metrics
        metrics = {
            "deployment_frequency_per_day": 2.5,
            "lead_time_hours": 1.5,
            "mttr_hours": 0.5,
            "change_failure_rate": 5.0,
            "classification": "Elite",
        }

        # When: generating markdown report
        from scripts.ci.dora_metrics import generate_markdown_report

        report = generate_markdown_report(metrics)

        # Then: report should contain metrics and classification
        assert "Elite" in report
        assert "2.5" in report  # deployment frequency
        assert "1.5" in report  # lead time

    def test_generate_trend_chart_data(self):
        """Test generating trend chart data for visualization"""
        # Given: historical metrics
        history = [
            {"timestamp": "2025-01-01", "deployment_frequency_per_day": 2.0},
            {"timestamp": "2025-01-02", "deployment_frequency_per_day": 2.5},
            {"timestamp": "2025-01-03", "deployment_frequency_per_day": 3.0},
        ]

        # When: generating chart data
        from scripts.ci.dora_metrics import generate_trend_data

        trend = generate_trend_data(history, "deployment_frequency_per_day")

        # Then: should return time series data
        assert len(trend) == 3
        assert trend[-1]["value"] == 3.0
