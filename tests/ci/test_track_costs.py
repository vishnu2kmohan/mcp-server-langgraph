"""
Test suite for GitHub Actions cost tracking script.

Following TDD approach - tests written before implementation.
Tests the cost analysis functionality for workflow runs.
"""

import gc
import json
from pathlib import Path

import pytest


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testloadruns")
class TestLoadRuns:
    """Test the load_runs() function that loads workflow runs from JSON files."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_runs_from_single_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading workflow runs from a single JSON file."""
        # Arrange
        workflow_data = {
            "workflow_runs": [
                {
                    "id": 1,
                    "name": "CI/CD Pipeline",
                    "run_duration_ms": 600000,
                    "status": "completed",
                },
                {
                    "id": 2,
                    "name": "Tests",
                    "run_duration_ms": 300000,
                    "status": "completed",
                },
            ]
        }

        runs_file = tmp_path / "workflow-runs.json"
        runs_file.write_text(json.dumps(workflow_data))

        # Change to tmp directory so script finds the file
        monkeypatch.chdir(tmp_path)
        from scripts.ci.track_costs import load_runs

        # Act
        runs = load_runs()

        # Assert
        assert len(runs) == 2
        assert runs[0]["name"] == "CI/CD Pipeline"
        assert runs[1]["name"] == "Tests"

    def test_load_runs_from_multiple_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading workflow runs from page 1 and page 2 JSON files."""
        # Arrange
        page1_data = {
            "workflow_runs": [
                {"id": 1, "name": "Workflow 1", "run_duration_ms": 100000},
            ]
        }
        page2_data = {
            "workflow_runs": [
                {"id": 2, "name": "Workflow 2", "run_duration_ms": 200000},
            ]
        }

        (tmp_path / "workflow-runs.json").write_text(json.dumps(page1_data))
        (tmp_path / "workflow-runs-page2.json").write_text(json.dumps(page2_data))

        monkeypatch.chdir(tmp_path)
        from scripts.ci.track_costs import load_runs

        # Act
        runs = load_runs()

        # Assert
        assert len(runs) == 2
        assert runs[0]["id"] == 1
        assert runs[1]["id"] == 2

    def test_load_runs_missing_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load_runs() returns empty list when files don't exist."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        from scripts.ci.track_costs import load_runs

        # Act
        runs = load_runs()

        # Assert
        assert runs == []

    def test_load_runs_malformed_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load_runs() handles malformed JSON gracefully."""
        # Arrange
        runs_file = tmp_path / "workflow-runs.json"
        runs_file.write_text("{ invalid json }")

        monkeypatch.chdir(tmp_path)
        from scripts.ci.track_costs import load_runs

        # Act
        runs = load_runs()

        # Assert
        assert runs == []

    def test_load_runs_empty_workflow_runs_array(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load_runs() with valid JSON but empty workflow_runs."""
        # Arrange
        workflow_data = {"workflow_runs": []}

        runs_file = tmp_path / "workflow-runs.json"
        runs_file.write_text(json.dumps(workflow_data))

        monkeypatch.chdir(tmp_path)
        from scripts.ci.track_costs import load_runs

        # Act
        runs = load_runs()

        # Assert
        assert runs == []


@pytest.mark.xdist_group(name="testanalyzeusage")
class TestAnalyzeUsage:
    """Test the analyze_usage() function that analyzes workflow costs."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_analyze_usage_basic_calculation(self) -> None:
        """Test basic cost calculation for workflow runs."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {
                "name": "CI/CD Pipeline",
                "run_duration_ms": 600000,  # 10 minutes
            },
            {
                "name": "Tests",
                "run_duration_ms": 300000,  # 5 minutes
            },
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Total Runs:** 2" in report
        assert "Total Minutes:** 15.0 min (15 billable)" in report
        # 15 minutes * $0.008/min = $0.12
        assert "Estimated Cost:** $0.12" in report

    def test_analyze_usage_weekly_budget_calculation(self) -> None:
        """Test weekly budget calculation and status."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        # 1400 minutes = 93.3% of 1500 minute weekly budget
        runs = [
            {"name": "Workflow 1", "run_duration_ms": 1400 * 60 * 1000},
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Weekly Budget Status" in report
        assert "Budget:** 1500 minutes" in report
        assert "Utilization:** 93.3%" in report
        assert "🟡" in report  # Yellow emoji for 80-100% utilization

    def test_analyze_usage_monthly_budget_calculation(self) -> None:
        """Test monthly budget calculation."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Workflow 1", "run_duration_ms": 5000 * 60 * 1000},  # 5000 minutes
        ]

        # Act
        report = analyze_usage(runs, period_days=30)

        # Assert
        assert "Monthly Budget Status" in report
        assert "Budget:** 6000 minutes" in report
        assert "Utilization:** 83.3%" in report

    def test_analyze_usage_over_budget(self) -> None:
        """Test cost analysis when over budget."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Expensive Workflow", "run_duration_ms": 1600 * 60 * 1000},  # 1600 minutes
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Utilization:** 106.7%" in report  # 1600/1500 = 106.7%
        assert "🔴" in report  # Red emoji for over budget
        assert "Remaining:** -100 minutes" in report

    def test_analyze_usage_under_budget(self) -> None:
        """Test cost analysis when well under budget."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Fast Workflow", "run_duration_ms": 100 * 60 * 1000},  # 100 minutes
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Utilization:** 6.7%" in report  # 100/1500 = 6.7%
        assert "✅" in report  # Green emoji for under 80%
        assert "Remaining:** 1400 minutes" in report

    def test_analyze_usage_duration_rounding(self) -> None:
        """Test billable minutes are rounded up correctly."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            # 2.3 minutes should round to 3 billable minutes
            {"name": "Workflow 1", "run_duration_ms": 138000},  # 2.3 minutes
            # 5.0 minutes should be exactly 5 billable minutes
            {"name": "Workflow 2", "run_duration_ms": 300000},  # 5.0 minutes
            # 0.1 minutes should round to 1 billable minute
            {"name": "Workflow 3", "run_duration_ms": 6000},  # 0.1 minutes
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        # Total: 2.3 + 5.0 + 0.1 = 7.4 actual minutes
        # Billable: 3 + 5 + 1 = 9 billable minutes
        assert "Total Minutes:** 7.4 min (9 billable)" in report
        assert "Estimated Cost:** $0.07" in report  # 9 * $0.008 = $0.072 ≈ $0.07

    def test_analyze_usage_workflow_grouping(self) -> None:
        """Test workflows are grouped correctly in the report."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "CI/CD Pipeline", "run_duration_ms": 600000},  # 10 min
            {"name": "CI/CD Pipeline", "run_duration_ms": 480000},  # 8 min
            {"name": "Tests", "run_duration_ms": 300000},  # 5 min
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Top Workflows by Cost" in report
        # CI/CD Pipeline: 2 runs, 18 total minutes, should be first
        assert "CI/CD Pipeline | 2 |" in report
        assert "Tests | 1 |" in report

    def test_analyze_usage_high_duration_workflows(self) -> None:
        """Test identification of high duration workflows."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            # Average: 20 minutes (over 15 minute threshold)
            {"name": "Slow Workflow", "run_duration_ms": 1200000},
            {"name": "Slow Workflow", "run_duration_ms": 1200000},
            # Average: 5 minutes (under threshold)
            {"name": "Fast Workflow", "run_duration_ms": 300000},
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "High Duration Workflows (>15 min avg)" in report
        assert "Slow Workflow**: 20.0 min avg" in report
        assert "Fast Workflow" not in report.split("High Duration Workflows")[1]

    def test_analyze_usage_high_frequency_workflows(self) -> None:
        """Test identification of high frequency workflows."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        # Create 25 runs of the same workflow (over 20 run threshold)
        runs = [{"name": "Frequent Workflow", "run_duration_ms": 60000} for _ in range(25)]
        # Add a workflow with fewer runs
        runs.append({"name": "Rare Workflow", "run_duration_ms": 60000})

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "High Frequency Workflows (>20 runs)" in report
        assert "Frequent Workflow**: 25 runs" in report
        assert "Rare Workflow" not in report.split("High Frequency Workflows")[1]

    def test_analyze_usage_empty_runs(self) -> None:
        """Test analyze_usage() with no workflow runs."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = []

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Total Runs:** 0" in report
        assert "Total Minutes:** 0.0 min (0 billable)" in report
        assert "Estimated Cost:** $0.00" in report
        assert "Utilization:** 0.0%" in report

    def test_analyze_usage_metrics_file_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that metrics are saved to cost-metrics.txt file."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Workflow", "run_duration_ms": 600000},  # 10 minutes
        ]

        monkeypatch.chdir(tmp_path)
        # Act
        analyze_usage(runs, period_days=7)

        # Assert
        metrics_file = tmp_path / "cost-metrics.txt"
        assert metrics_file.exists()

        content = metrics_file.read_text()
        assert "total_minutes=10.0" in content
        assert "billable_minutes=10" in content
        assert "total_cost=0.08" in content  # 10 * 0.008
        assert "budget_pct=0.7" in content  # 10/1500 * 100 = 0.67%
        assert "budget_remaining=1490" in content

    def test_analyze_usage_report_file_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that report is saved to cost-report.md file."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Test Workflow", "run_duration_ms": 300000},
        ]

        monkeypatch.chdir(tmp_path)
        # Act
        analyze_usage(runs, period_days=7)

        # Assert
        report_file = tmp_path / "cost-report.md"
        assert report_file.exists()

        content = report_file.read_text()
        assert "# GitHub Actions Cost Report (7 days)" in content
        assert "Test Workflow" in content

    def test_analyze_usage_missing_duration_field(self) -> None:
        """Test handling of runs with missing run_duration_ms field."""
        # Arrange
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Workflow 1", "run_duration_ms": 600000},
            {"name": "Workflow 2"},  # Missing run_duration_ms
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Total Runs:** 2" in report
        # Only first workflow's duration counted
        assert "Total Minutes:** 10.0 min" in report


@pytest.mark.xdist_group(name="testcostconstants")
class TestCostConstants:
    """Test cost constants are correct."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cost_per_minute_constant(self) -> None:
        """Test COST_PER_MIN_LINUX constant is correct."""
        from scripts.ci.track_costs import COST_PER_MIN_LINUX

        assert COST_PER_MIN_LINUX == 0.008

    def test_weekly_budget_constant(self) -> None:
        """Test WEEKLY_BUDGET_MINS constant is correct."""
        from scripts.ci.track_costs import WEEKLY_BUDGET_MINS

        assert WEEKLY_BUDGET_MINS == 1500

    def test_monthly_budget_constant(self) -> None:
        """Test MONTHLY_BUDGET_MINS constant is correct."""
        from scripts.ci.track_costs import MONTHLY_BUDGET_MINS

        assert MONTHLY_BUDGET_MINS == 6000


@pytest.mark.xdist_group(name="testmainexecution")
class TestMainExecution:
    """Test the main execution flow of the script."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_main_uses_environment_variable_for_period(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main() reads PERIOD_DAYS from environment."""
        # Arrange
        workflow_data = {
            "workflow_runs": [
                {"name": "Test", "run_duration_ms": 60000},
            ]
        }
        (tmp_path / "workflow-runs.json").write_text(json.dumps(workflow_data))

        monkeypatch.setenv("PERIOD_DAYS", "30")
        monkeypatch.chdir(tmp_path)

        # Act
        from scripts.ci.track_costs import main

        main()

        # Assert
        report_file = tmp_path / "cost-report.md"
        content = report_file.read_text()
        assert "# GitHub Actions Cost Report (30 days)" in content
        assert "Monthly Budget Status" in content

    def test_main_defaults_to_7_days(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main() defaults to 7 days when PERIOD_DAYS not set."""
        # Arrange
        workflow_data = {
            "workflow_runs": [
                {"name": "Test", "run_duration_ms": 60000},
            ]
        }
        (tmp_path / "workflow-runs.json").write_text(json.dumps(workflow_data))

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PERIOD_DAYS", raising=False)

        # Act
        from scripts.ci.track_costs import main

        main()

        # Assert
        report_file = tmp_path / "cost-report.md"
        content = report_file.read_text()
        assert "# GitHub Actions Cost Report (7 days)" in content
        assert "Weekly Budget Status" in content


@pytest.mark.xdist_group(name="testedgecases")
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_zero_duration_workflow(self) -> None:
        """Test workflow with 0 duration."""
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "Zero Duration", "run_duration_ms": 0},
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "Total Minutes:** 0.0 min (0 billable)" in report

    def test_very_large_duration(self) -> None:
        """Test workflow with very large duration."""
        from scripts.ci.track_costs import analyze_usage

        # 10 hours = 600 minutes
        runs = [
            {"name": "Long Workflow", "run_duration_ms": 36000000},
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        assert "600.0 min (600 billable)" in report
        assert "Estimated Cost:** $4.80" in report

    def test_workflow_name_with_special_characters(self) -> None:
        """Test workflow names with special markdown characters."""
        from scripts.ci.track_costs import analyze_usage

        runs = [
            {"name": "CI/CD | Pipeline & Tests", "run_duration_ms": 60000},
        ]

        # Act
        report = analyze_usage(runs, period_days=7)

        # Assert
        # Should not break markdown table formatting
        assert "CI/CD | Pipeline & Tests" in report

    def test_hundreds_of_workflow_runs(self) -> None:
        """Test performance with large number of runs."""
        from scripts.ci.track_costs import analyze_usage

        # Create 500 runs
        runs = [{"name": f"Workflow {i % 10}", "run_duration_ms": 60000} for i in range(500)]

        # Act
        report = analyze_usage(runs, period_days=30)

        # Assert
        assert "Total Runs:** 500" in report
        # Should show top 10 workflows only
        assert report.count(" | ") >= 10  # At least 10 table rows
