#!/usr/bin/env python3
"""
DORA Metrics Calculator for GitHub Actions

Calculates the four key DevOps Research and Assessment (DORA) metrics:
1. Deployment Frequency: How often code is deployed to production
2. Lead Time for Changes: Time from commit to production deployment
3. Mean Time to Recovery (MTTR): Time to restore service after incident
4. Change Failure Rate: Percentage of deployments causing failures

Classification:
- Elite: DF (multiple/day), LT (<1 hour), MTTR (<1 hour), CFR (<5%)
- High: DF (weekly-monthly), LT (<1 day), MTTR (<1 day), CFR (<10%)
- Medium: DF (monthly-bimonthly), LT (<1 week), MTTR (<1 day), CFR (<15%)
- Low: DF (< bimonthly), LT (>1 week), MTTR (>1 day), CFR (>15%)

Usage:
    python dora_metrics.py --repo owner/repo --days 30 --output metrics.json

Requires:
    - GitHub CLI (gh) installed and authenticated
    - GitHub token with repo and actions:read permissions
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def run_gh_command(args: list[str]) -> str:
    """Run gh CLI command and return output."""
    try:
        result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def calculate_deployment_frequency(deployments: list[dict[str, Any]], days: int) -> float:
    """
    Calculate deployment frequency (deployments per day).

    Args:
        deployments: List of deployment records with timestamp
        days: Number of days in the analysis period

    Returns:
        Deployment frequency as deployments per day
    """
    if not deployments or days <= 0:
        return 0.0

    return len(deployments) / days


def calculate_lead_time(commits: list[dict[str, Any]], deployment: dict[str, Any]) -> float:
    """
    Calculate lead time from first commit to deployment.

    Args:
        commits: List of commits with timestamp
        deployment: Deployment record with timestamp and associated commits

    Returns:
        Lead time in hours
    """
    if not commits:
        return 0.0

    # Parse timestamps
    first_commit_time = datetime.fromisoformat(commits[0]["timestamp"].replace("Z", "+00:00"))
    deployment_time = datetime.fromisoformat(deployment["timestamp"].replace("Z", "+00:00"))

    # Calculate difference in hours
    lead_time_delta = deployment_time - first_commit_time
    lead_time_hours = lead_time_delta.total_seconds() / 3600

    return lead_time_hours


def calculate_mttr(incident: dict[str, Any], recovery_deployment: dict[str, Any]) -> float:
    """
    Calculate Mean Time to Recovery from incident to recovery deployment.

    Args:
        incident: Incident record with detected_at timestamp
        recovery_deployment: Recovery deployment record with timestamp

    Returns:
        MTTR in hours
    """
    # Parse timestamps
    incident_time = datetime.fromisoformat(incident["detected_at"].replace("Z", "+00:00"))
    recovery_time = datetime.fromisoformat(recovery_deployment["timestamp"].replace("Z", "+00:00"))

    # Calculate difference in hours
    mttr_delta = recovery_time - incident_time
    mttr_hours = mttr_delta.total_seconds() / 3600

    return mttr_hours


def calculate_change_failure_rate(deployments: list[dict[str, Any]]) -> float:
    """
    Calculate change failure rate as percentage of failed deployments.

    Args:
        deployments: List of deployments with status field

    Returns:
        Failure rate as percentage (0-100)
    """
    if not deployments:
        return 0.0

    failed_count = sum(1 for d in deployments if d.get("status") == "failed")
    total_count = len(deployments)

    failure_rate = (failed_count / total_count) * 100
    return failure_rate


def classify_dora_performance(metrics: dict[str, float]) -> str:
    """
    Classify DORA performance based on the four key metrics.

    Args:
        metrics: Dictionary with deployment_frequency_per_day, lead_time_hours,
                mttr_hours, and change_failure_rate

    Returns:
        Performance classification: "Elite", "High", "Medium", or "Low"
    """
    df = metrics.get("deployment_frequency_per_day", 0)
    lt = metrics.get("lead_time_hours", float("inf"))
    mttr = metrics.get("mttr_hours", float("inf"))
    cfr = metrics.get("change_failure_rate", 100)

    # Elite: On-demand deployments, <1hr lead time, <1hr MTTR, <15% CFR
    if df >= 1 and lt < 1 and mttr < 1 and cfr <= 15:
        return "Elite"

    # High: Weekly-monthly deployments, <1 day lead time, <1 day MTTR, <15% CFR
    if df >= 1 / 7 and lt < 24 and mttr < 24 and cfr <= 15:
        return "High"

    # Medium: Monthly deployments, <1 week lead time, <1 week MTTR, <30% CFR
    if df >= 1 / 30 and lt < 720 and mttr < 168 and cfr <= 30:
        return "Medium"

    # Low: All others
    return "Low"


# GitHub API mock support (for testing)
class GitHubClient:
    """Mock GitHub client for testing."""

    def get_deployments(self) -> list[dict[str, Any]]:
        """Get deployment data from GitHub API."""
        return []

    def get_commits(self) -> list[dict[str, Any]]:
        """Get commit data from GitHub API."""
        return []


def collect_deployment_data(repo: str, days: int = 30) -> list[dict[str, Any]]:
    """
    Collect deployment data from GitHub API.

    Args:
        repo: Repository in format owner/repo
        days: Number of days to look back

    Returns:
        List of deployment records
    """
    client = GitHubClient()
    raw_deployments = client.get_deployments()

    # Transform raw deployment data
    deployments = []
    for d in raw_deployments:
        deployment = {
            "environment": d.get("environment"),
            "timestamp": d.get("created_at"),
            "status": d.get("statuses", [{}])[0].get("state", "unknown"),
        }
        deployments.append(deployment)

    return deployments


def collect_commit_data(repo: str, since: str) -> list[dict[str, Any]]:
    """
    Collect commit data from GitHub API.

    Args:
        repo: Repository in format owner/repo
        since: ISO 8601 date string for cutoff

    Returns:
        List of commit records
    """
    client = GitHubClient()
    raw_commits = client.get_commits()

    # Transform raw commit data
    commits = []
    for c in raw_commits:
        commit = {
            "sha": c.get("sha"),
            "timestamp": c.get("commit", {}).get("author", {}).get("date"),
            "message": c.get("commit", {}).get("message"),
        }
        commits.append(commit)

    return commits


def save_metrics(metrics: dict[str, Any], output_file: Path) -> None:
    """
    Save metrics to JSON file (appends to existing history).

    Args:
        metrics: Metrics dictionary to save
        output_file: Path to output file
    """
    # Load existing metrics if file exists
    existing_metrics = []
    if output_file.exists():
        try:
            existing_metrics = json.loads(output_file.read_text())
            if not isinstance(existing_metrics, list):
                existing_metrics = [existing_metrics]
        except (json.JSONDecodeError, ValueError):
            existing_metrics = []

    # Append new metrics
    existing_metrics.append(metrics)

    # Write back
    output_file.write_text(json.dumps(existing_metrics, indent=2))


def load_historical_metrics(metrics_file: Path) -> list[dict[str, Any]]:
    """
    Load historical metrics from JSON file.

    Args:
        metrics_file: Path to metrics file

    Returns:
        List of historical metrics
    """
    if not metrics_file.exists():
        return []

    try:
        data = json.loads(metrics_file.read_text())
        if isinstance(data, list):
            return data
        return [data]
    except (json.JSONDecodeError, ValueError):
        return []


def generate_markdown_report(metrics: dict[str, Any]) -> str:
    """
    Generate markdown report for DORA metrics.

    Args:
        metrics: Metrics dictionary

    Returns:
        Markdown-formatted report
    """
    report = f"""# DORA Metrics Report

## Overall Classification: {metrics.get('classification', 'Unknown')}

### Key Metrics

- **Deployment Frequency:** {metrics.get('deployment_frequency_per_day', 0):.2f} deployments/day
- **Lead Time for Changes:** {metrics.get('lead_time_hours', 0):.2f} hours
- **Mean Time to Recovery:** {metrics.get('mttr_hours', 0):.2f} hours
- **Change Failure Rate:** {metrics.get('change_failure_rate', 0):.1f}%

### Classification Thresholds

- **Elite:** Multiple deployments per day, <1hr lead time, <1hr MTTR, <15% failure rate
- **High:** Weekly deployments, <1 day lead time, <1 day MTTR, <15% failure rate
- **Medium:** Monthly deployments, <1 week lead time, <1 week MTTR, <30% failure rate
- **Low:** Below medium thresholds
"""
    return report


def generate_trend_data(history: list[dict[str, Any]], metric_key: str) -> list[dict[str, Any]]:
    """
    Generate trend chart data for a specific metric.

    Args:
        history: Historical metrics list
        metric_key: Key of the metric to extract

    Returns:
        List of time series data points
    """
    trend = []
    for record in history:
        if metric_key in record:
            trend.append({"timestamp": record.get("timestamp"), "value": record[metric_key]})

    return trend


def calculate_deployment_frequency_cli(repo: str, days: int) -> tuple[float, str]:
    """Calculate deployment frequency (deployments per day) from GitHub CLI."""
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    # Query for successful deployment workflow runs
    cmd = [
        "api",
        f"repos/{repo}/actions/runs",
        "--paginate",
        "-X",
        "GET",
        "-f",
        "status=completed",
        "-f",
        "conclusion=success",
        "-f",
        f"created>={cutoff_date}",
        "--jq",
        '.workflow_runs[] | select(.name | contains("Production") or contains("Deploy")) | {id, created_at, name}',
    ]

    output = run_gh_command(cmd)

    if not output.strip():
        return 0.0, "Low"

    # Count deployments
    deployments = [json.loads(line) for line in output.strip().split("\n") if line.strip()]
    deployment_count = len(deployments)

    # Calculate frequency
    frequency_per_day = deployment_count / days if days > 0 else 0

    # Classify
    if frequency_per_day >= 1:
        classification = "Elite"
    elif frequency_per_day >= 1 / 7:  # Weekly
        classification = "High"
    elif frequency_per_day >= 1 / 30:  # Monthly
        classification = "Medium"
    else:
        classification = "Low"

    return frequency_per_day, classification


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Calculate DORA metrics from GitHub Actions")
    parser.add_argument("--repo", required=True, help="Repository in format owner/repo")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--verbose", action="store_true", help="Print detailed output")

    args = parser.parse_args()

    print(f"Calculating DORA metrics for {args.repo} (last {args.days} days)...")
    print("")

    # Calculate deployment frequency only for now (stub for other metrics)
    print("📊 Deployment Frequency...")
    df_value, df_class = calculate_deployment_frequency_cli(args.repo, args.days)
    print(f"  Value: {df_value:.2f} deployments/day")
    print(f"  Classification: {df_class}")
    print("")

    # Create output
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "repository": args.repo,
        "analysis_period_days": args.days,
        "deployment_frequency": {
            "value": round(df_value, 2),
            "unit": "deployments_per_day",
            "classification": df_class,
        },
        "overall_classification": df_class,
        "note": "Full DORA metrics implementation in progress",
    }

    # Write output
    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Metrics saved to {args.output}")


if __name__ == "__main__":
    main()
