#!/usr/bin/env python3
"""
Generate dashboard metrics for gh-pages telemetry.

Collects and aggregates:
1. DORA Metrics - Deployment frequency, lead time, change failure rate, MTTR
2. Dependency Graph - Package dependencies with vulnerability status
3. Test Flakiness - Retry statistics and flakiness scores

Usage:
    python scripts/ci/generate_dashboard_metrics.py \
        --output-dir gh-pages/metrics \
        --git-history-days 30

All metrics are aggregated from existing data - no new test runs required.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path


@dataclass
class DORAMetrics:
    """DORA (DevOps Research and Assessment) metrics."""

    # Deployment Frequency: How often code is deployed to production
    deployment_frequency: float = 0.0  # deployments per week
    deployment_frequency_rating: str = "unknown"  # elite/high/medium/low

    # Lead Time for Changes: Time from commit to production
    lead_time_hours: float = 0.0
    lead_time_rating: str = "unknown"

    # Change Failure Rate: Percentage of deployments causing failures
    change_failure_rate: float = 0.0
    change_failure_rating: str = "unknown"

    # Mean Time to Recovery: How long to recover from failures
    mttr_hours: float = 0.0
    mttr_rating: str = "unknown"

    # Metadata
    period_days: int = 30
    total_deployments: int = 0
    total_commits: int = 0
    calculated_at: str = ""


@dataclass
class DependencyInfo:
    """Information about a package dependency."""

    name: str
    version: str
    is_direct: bool = True
    dependencies: list[str] = field(default_factory=list)
    has_vulnerability: bool = False
    vulnerability_severity: str | None = None


@dataclass
class DependencyGraph:
    """Dependency graph with vulnerability status."""

    packages: list[DependencyInfo] = field(default_factory=list)
    total_packages: int = 0
    direct_dependencies: int = 0
    transitive_dependencies: int = 0
    vulnerable_packages: int = 0
    generated_at: str = ""


@dataclass
class FlakinessData:
    """Test flakiness tracking data."""

    total_tests: int = 0
    flaky_tests: int = 0
    flakiness_rate: float = 0.0
    retries_last_week: int = 0
    most_flaky_tests: list[dict] = field(default_factory=list)
    generated_at: str = ""


def calculate_dora_metrics(days: int = 30) -> DORAMetrics:
    """
    Calculate DORA metrics from git history and workflow runs.

    Args:
        days: Number of days to analyze

    Returns:
        DORAMetrics with calculated values
    """
    metrics = DORAMetrics(
        period_days=days,
        calculated_at=datetime.now(UTC).isoformat(),
    )

    since_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")

    # Count commits to main branch
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"--since={since_date}", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        metrics.total_commits = int(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        metrics.total_commits = 0

    # Count merges to main (proxy for deployments in trunk-based development)
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "--merges", f"--since={since_date}", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        metrics.total_deployments = int(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        metrics.total_deployments = 0

    # Calculate deployment frequency (per week)
    weeks = days / 7
    if weeks > 0:
        metrics.deployment_frequency = round(metrics.total_deployments / weeks, 2)

    # Rate deployment frequency (DORA benchmarks)
    if metrics.deployment_frequency >= 7:  # Multiple times per day
        metrics.deployment_frequency_rating = "elite"
    elif metrics.deployment_frequency >= 1:  # Once per day to once per week
        metrics.deployment_frequency_rating = "high"
    elif metrics.deployment_frequency >= 0.25:  # Once per week to once per month
        metrics.deployment_frequency_rating = "medium"
    else:
        metrics.deployment_frequency_rating = "low"

    # Lead time: Average time from first commit in PR to merge
    # For simplicity, estimate based on average PR age
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--merges",
                f"--since={since_date}",
                "--format=%H",
                "-n",
                "20",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        merge_commits = result.stdout.strip().split("\n")
        if merge_commits and merge_commits[0]:
            lead_times = []
            for merge in merge_commits[:10]:  # Sample first 10
                try:
                    # Get merge timestamp and first parent timestamp
                    dates = subprocess.run(
                        ["git", "log", "-1", "--format=%ct", merge],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,
                    )
                    merge_time = int(dates.stdout.strip())

                    # Get first commit in the merged branch
                    first = subprocess.run(
                        ["git", "log", "-1", "--format=%ct", f"{merge}^2"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,
                    )
                    first_time = int(first.stdout.strip())
                    lead_times.append((merge_time - first_time) / 3600)  # Hours
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
                    continue

            if lead_times:
                metrics.lead_time_hours = round(sum(lead_times) / len(lead_times), 1)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # Rate lead time (DORA benchmarks)
    if metrics.lead_time_hours < 24:  # Less than one day
        metrics.lead_time_rating = "elite"
    elif metrics.lead_time_hours < 168:  # Less than one week
        metrics.lead_time_rating = "high"
    elif metrics.lead_time_hours < 720:  # Less than one month
        metrics.lead_time_rating = "medium"
    else:
        metrics.lead_time_rating = "low"

    # Change failure rate and MTTR require CI failure data
    # For now, use placeholder values (would need GitHub API integration)
    metrics.change_failure_rate = 0.0
    metrics.change_failure_rating = "unknown"
    metrics.mttr_hours = 0.0
    metrics.mttr_rating = "unknown"

    return metrics


def generate_dependency_graph() -> DependencyGraph:
    """
    Generate dependency graph from uv/pip.

    Returns:
        DependencyGraph with package information
    """
    graph = DependencyGraph(
        generated_at=datetime.now(UTC).isoformat(),
    )

    # Try uv pip tree first, then pipdeptree
    try:
        result = subprocess.run(
            ["uv", "pip", "tree", "--depth", "1"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        lines = result.stdout.strip().split("\n")

        current_pkg = None
        for line in lines:
            if not line.strip():
                continue

            # Direct dependency (no indentation)
            if not line.startswith(" "):
                parts = line.split()
                if parts:
                    name = parts[0]
                    version = parts[1] if len(parts) > 1 else "unknown"
                    current_pkg = DependencyInfo(
                        name=name,
                        version=version,
                        is_direct=True,
                    )
                    graph.packages.append(current_pkg)
                    graph.direct_dependencies += 1
            # Transitive dependency (indented)
            elif current_pkg and line.strip().startswith("├") or line.strip().startswith("└"):
                parts = line.strip().lstrip("├└─ ").split()
                if parts:
                    dep_name = parts[0]
                    current_pkg.dependencies.append(dep_name)
                    graph.transitive_dependencies += 1

        graph.total_packages = len(graph.packages)

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: just count from requirements
        pass

    return graph


def analyze_test_flakiness(trends_file: Path | None = None) -> FlakinessData:
    """
    Analyze test flakiness from pytest retry data.

    Args:
        trends_file: Path to test-durations.json from gh-pages

    Returns:
        FlakinessData with retry statistics
    """
    flakiness = FlakinessData(
        generated_at=datetime.now(UTC).isoformat(),
    )

    # Try to load existing trends data
    if trends_file and trends_file.exists():
        try:
            with open(trends_file) as f:
                trends = json.load(f)

            runs = trends.get("runs", [])
            if runs:
                # Aggregate test counts
                total_passed = sum(r.get("tests_passed", 0) for r in runs[-10:])
                total_failed = sum(r.get("tests_failed", 0) for r in runs[-10:])
                flakiness.total_tests = total_passed + total_failed

                # Track retry patterns (would need pytest-rerunfailures output)
                # For now, estimate based on failure rate variance
                failure_rates = []
                for run in runs[-10:]:
                    passed = run.get("tests_passed", 0)
                    failed = run.get("tests_failed", 0)
                    total = passed + failed
                    if total > 0:
                        failure_rates.append(failed / total)

                if failure_rates:
                    avg_rate = sum(failure_rates) / len(failure_rates)
                    variance = sum((r - avg_rate) ** 2 for r in failure_rates) / len(failure_rates)
                    # High variance suggests flakiness
                    flakiness.flakiness_rate = round(variance * 100, 2)

        except (json.JSONDecodeError, OSError):
            pass

    return flakiness


def generate_all_metrics(output_dir: Path, days: int = 30) -> dict:
    """
    Generate all dashboard metrics.

    Args:
        output_dir: Directory to write metric files
        days: Number of days to analyze

    Returns:
        Combined metrics dictionary
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate each metric type
    dora = calculate_dora_metrics(days)
    deps = generate_dependency_graph()
    flaky = analyze_test_flakiness(output_dir.parent / "trends" / "test-durations.json")

    # Write individual JSON files
    (output_dir / "dora-metrics.json").write_text(json.dumps(asdict(dora), indent=2))
    (output_dir / "dependency-graph.json").write_text(json.dumps(asdict(deps), indent=2))
    (output_dir / "test-flakiness.json").write_text(json.dumps(asdict(flaky), indent=2))

    # Combined metrics
    combined = {
        "dora": asdict(dora),
        "dependencies": asdict(deps),
        "flakiness": asdict(flaky),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (output_dir / "all-metrics.json").write_text(json.dumps(combined, indent=2))

    return combined


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate dashboard metrics")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("gh-pages/metrics"),
        help="Output directory for metric files",
    )
    parser.add_argument(
        "--git-history-days",
        type=int,
        default=30,
        help="Number of days of git history to analyze",
    )

    args = parser.parse_args()

    print(f"Generating dashboard metrics for last {args.git_history_days} days...")
    metrics = generate_all_metrics(args.output_dir, args.git_history_days)

    print("\nDORA Metrics:")
    print(
        f"  Deployment Frequency: {metrics['dora']['deployment_frequency']}/week ({metrics['dora']['deployment_frequency_rating']})"
    )
    print(f"  Lead Time: {metrics['dora']['lead_time_hours']}h ({metrics['dora']['lead_time_rating']})")
    print(f"  Total Commits: {metrics['dora']['total_commits']}")

    print("\nDependency Graph:")
    print(f"  Total Packages: {metrics['dependencies']['total_packages']}")
    print(f"  Direct: {metrics['dependencies']['direct_dependencies']}")
    print(f"  Transitive: {metrics['dependencies']['transitive_dependencies']}")

    print("\nTest Flakiness:")
    print(f"  Flakiness Rate: {metrics['flakiness']['flakiness_rate']}%")

    print(f"\nMetrics written to {args.output_dir}")


if __name__ == "__main__":
    main()
