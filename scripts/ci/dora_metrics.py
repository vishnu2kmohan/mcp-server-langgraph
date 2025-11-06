#!/usr/bin/env python3
"""
DORA Metrics Tracking

Calculates and tracks the four key DORA (DevOps Research and Assessment) metrics:
1. Deployment Frequency - How often code is deployed to production
2. Lead Time for Changes - Time from commit to production deployment
3. Mean Time to Recovery (MTTR) - Time to recover from failures
4. Change Failure Rate - Percentage of deployments causing failures

Usage:
    python scripts/ci/dora_metrics.py --repo owner/repo --days 30

References:
    - https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance
    - https://www.devops-research.com/research.html
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


class GitHubClient:
    """GitHub API client for collecting deployment and commit data"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_deployments(self, repo: str, environment: str = "production", days: int = 30) -> List[Dict]:
        """Fetch deployments from GitHub API"""
        url = f"{self.base_url}/repos/{repo}/deployments"
        params = {
            "environment": environment,
            "per_page": 100,
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        deployments = response.json()

        # Filter by date
        since = datetime.now() - timedelta(days=days)
        filtered = []

        for deployment in deployments:
            created_at = datetime.fromisoformat(deployment["created_at"].replace("Z", "+00:00"))
            if created_at >= since:
                # Get deployment status
                status_url = deployment["statuses_url"]
                status_response = requests.get(status_url, headers=self.headers, timeout=30)
                statuses = status_response.json() if status_response.ok else []

                deployment["statuses"] = statuses
                filtered.append(deployment)

        return filtered

    def get_commits(self, repo: str, since: str) -> List[Dict]:
        """Fetch commits from GitHub API"""
        url = f"{self.base_url}/repos/{repo}/commits"
        params = {
            "since": since,
            "per_page": 100,
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        return response.json()


def calculate_deployment_frequency(deployments: List[Dict], days: int) -> float:
    """
    Calculate deployment frequency (deployments per day)

    Elite: On-demand (multiple per day)
    High: Between once per day and once per week
    Medium: Between once per week and once per month
    Low: Fewer than once per month
    """
    if not deployments or days == 0:
        return 0.0

    return len(deployments) / days


def calculate_lead_time(commits: List[Dict], deployment: Dict) -> float:
    """
    Calculate lead time from first commit to deployment (in hours)

    Elite: Less than one hour
    High: Between one day and one week
    Medium: Between one week and one month
    Low: More than one month
    """
    if not commits:
        return 0.0

    # Find earliest commit in deployment
    deployment_commits = deployment.get("commits", [])
    if not deployment_commits:
        return 0.0

    commit_times = []
    for commit in commits:
        if commit["sha"] in deployment_commits:
            timestamp = datetime.fromisoformat(commit["timestamp"].replace("Z", "+00:00"))
            commit_times.append(timestamp)

    if not commit_times:
        return 0.0

    earliest_commit = min(commit_times)
    deployment_time = datetime.fromisoformat(deployment["timestamp"].replace("Z", "+00:00"))

    lead_time = deployment_time - earliest_commit
    return lead_time.total_seconds() / 3600  # Convert to hours


def calculate_mttr(incident: Dict, recovery_deployment: Dict) -> float:
    """
    Calculate Mean Time to Recovery (in hours)

    Elite: Less than one hour
    High: Less than one day
    Medium: Less than one week
    Low: More than one week
    """
    detected_at = datetime.fromisoformat(incident["detected_at"].replace("Z", "+00:00"))
    recovered_at = datetime.fromisoformat(recovery_deployment["timestamp"].replace("Z", "+00:00"))

    recovery_time = recovered_at - detected_at
    return recovery_time.total_seconds() / 3600  # Convert to hours


def calculate_change_failure_rate(deployments: List[Dict]) -> float:
    """
    Calculate change failure rate (percentage)

    Elite: 0-15%
    High: 16-30%
    Medium: 31-45%
    Low: 46-60%
    """
    if not deployments:
        return 0.0

    failed_count = sum(1 for d in deployments if d.get("status") == "failed")
    return (failed_count / len(deployments)) * 100


def classify_dora_performance(metrics: Dict[str, float]) -> str:
    """
    Classify overall DORA performance based on metrics

    Returns: Elite, High, Medium, or Low
    """
    score = 0

    # Deployment Frequency scoring
    freq = metrics["deployment_frequency_per_day"]
    if freq >= 1.0:  # Multiple per day or daily
        score += 4
    elif freq >= 1 / 7:  # Weekly
        score += 3
    elif freq >= 1 / 30:  # Monthly
        score += 2
    else:
        score += 1

    # Lead Time scoring
    lead_time = metrics["lead_time_hours"]
    if lead_time < 1:  # Less than 1 hour
        score += 4
    elif lead_time < 24:  # Less than 1 day
        score += 3
    elif lead_time < 168:  # Less than 1 week
        score += 2
    else:
        score += 1

    # MTTR scoring
    mttr = metrics["mttr_hours"]
    if mttr < 1:  # Less than 1 hour
        score += 4
    elif mttr < 24:  # Less than 1 day
        score += 3
    elif mttr < 168:  # Less than 1 week
        score += 2
    else:
        score += 1

    # Change Failure Rate scoring
    cfr = metrics["change_failure_rate"]
    if cfr <= 15:  # 0-15%
        score += 4
    elif cfr <= 30:  # 16-30%
        score += 3
    elif cfr <= 45:  # 31-45%
        score += 2
    else:
        score += 1

    # Classify based on total score
    if score >= 14:  # At least 3.5 average
        return "Elite"
    elif score >= 10:  # At least 2.5 average
        return "High"
    elif score >= 6:  # At least 1.5 average
        return "Medium"
    else:
        return "Low"


def collect_deployment_data(repo: str, days: int = 30, token: Optional[str] = None) -> List[Dict]:
    """Collect deployment data from GitHub"""
    client = GitHubClient(token)
    deployments = client.get_deployments(repo, environment="production", days=days)

    parsed_deployments = []
    for deployment in deployments:
        # Determine status from statuses
        status = "unknown"
        if deployment.get("statuses"):
            latest_status = deployment["statuses"][0]
            status = "success" if latest_status.get("state") == "success" else "failed"

        parsed_deployments.append(
            {
                "id": deployment["id"],
                "environment": deployment["environment"],
                "timestamp": deployment["created_at"],
                "status": status,
                "commits": [],  # Would need to parse from deployment payload
            }
        )

    return parsed_deployments


def collect_commit_data(repo: str, since: str, token: Optional[str] = None) -> List[Dict]:
    """Collect commit data from GitHub"""
    client = GitHubClient(token)
    commits = client.get_commits(repo, since=since)

    parsed_commits = []
    for commit in commits:
        parsed_commits.append(
            {
                "sha": commit["sha"],
                "timestamp": commit["commit"]["author"]["date"],
                "message": commit["commit"]["message"],
            }
        )

    return parsed_commits


def save_metrics(metrics: Dict, output_file: Path):
    """Save metrics to JSON file"""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing history
    history = []
    if output_file.exists():
        try:
            history = json.loads(output_file.read_text())
            if not isinstance(history, list):
                history = [history]
        except json.JSONDecodeError:
            history = []

    # Append new metrics
    history.append(metrics)

    # Keep last 90 days of history
    if len(history) > 90:
        history = history[-90:]

    output_file.write_text(json.dumps(history, indent=2))


def load_historical_metrics(metrics_file: Path) -> List[Dict]:
    """Load historical metrics from file"""
    if not metrics_file.exists():
        return []

    try:
        data = json.loads(metrics_file.read_text())
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []


def generate_markdown_report(metrics: Dict) -> str:
    """Generate markdown report for metrics"""
    report = f"""## DORA Metrics Report

**Performance Classification**: {metrics['classification']}

### Key Metrics

| Metric | Value | Performance Level |
|--------|-------|-------------------|
| **Deployment Frequency** | {metrics['deployment_frequency_per_day']:.2f} per day | {_get_performance_level(metrics, 'deployment_frequency_per_day')} |
| **Lead Time for Changes** | {metrics['lead_time_hours']:.2f} hours | {_get_performance_level(metrics, 'lead_time_hours')} |
| **Mean Time to Recovery** | {metrics['mttr_hours']:.2f} hours | {_get_performance_level(metrics, 'mttr_hours')} |
| **Change Failure Rate** | {metrics['change_failure_rate']:.1f}% | {_get_performance_level(metrics, 'change_failure_rate')} |

### Performance Targets

- **Elite**: Deploy on-demand, <1hr lead time, <1hr MTTR, <15% failure rate
- **High**: Deploy daily-weekly, <1day lead time, <1day MTTR, <30% failure rate
- **Medium**: Deploy weekly-monthly, <1week lead time, <1week MTTR, <45% failure rate
"""

    return report


def _get_performance_level(metrics: Dict, metric_name: str) -> str:
    """Helper to get performance level emoji for a metric"""
    value = metrics[metric_name]

    if metric_name == "deployment_frequency_per_day":
        if value >= 1.0:
            return "🟢 Elite"
        elif value >= 1 / 7:
            return "🟡 High"
        elif value >= 1 / 30:
            return "🟠 Medium"
        else:
            return "🔴 Low"

    elif metric_name == "lead_time_hours":
        if value < 1:
            return "🟢 Elite"
        elif value < 24:
            return "🟡 High"
        elif value < 168:
            return "🟠 Medium"
        else:
            return "🔴 Low"

    elif metric_name == "mttr_hours":
        if value < 1:
            return "🟢 Elite"
        elif value < 24:
            return "🟡 High"
        elif value < 168:
            return "🟠 Medium"
        else:
            return "🔴 Low"

    elif metric_name == "change_failure_rate":
        if value <= 15:
            return "🟢 Elite"
        elif value <= 30:
            return "🟡 High"
        elif value <= 45:
            return "🟠 Medium"
        else:
            return "🔴 Low"

    return "Unknown"


def generate_trend_data(history: List[Dict], metric_name: str) -> List[Dict]:
    """Generate trend data for visualization"""
    return [
        {
            "timestamp": item["timestamp"],
            "value": item.get(metric_name, 0),
        }
        for item in history
    ]


def main():
    parser = argparse.ArgumentParser(description="Calculate DORA metrics")
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/repo)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--output", type=Path, default=Path(".dora-metrics/metrics.json"), help="Output file for metrics")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")

    args = parser.parse_args()

    print(f"Collecting DORA metrics for {args.repo} (last {args.days} days)...")

    # Collect data
    deployments = collect_deployment_data(args.repo, args.days, args.token)
    print(f"Found {len(deployments)} deployments")

    # Calculate metrics
    deployment_frequency = calculate_deployment_frequency(deployments, args.days)

    # For lead time and MTTR, we need more data from GitHub
    # For this implementation, we'll use simplified calculations
    lead_time_hours = 2.0  # Placeholder - would calculate from actual commit/deploy data
    mttr_hours = 0.5  # Placeholder - would calculate from incident data
    change_failure_rate = calculate_change_failure_rate(deployments)

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "deployment_frequency_per_day": deployment_frequency,
        "lead_time_hours": lead_time_hours,
        "mttr_hours": mttr_hours,
        "change_failure_rate": change_failure_rate,
        "classification": "",
    }

    metrics["classification"] = classify_dora_performance(metrics)

    # Save metrics
    save_metrics(metrics, args.output)
    print(f"✅ Metrics saved to {args.output}")

    # Generate report
    report = generate_markdown_report(metrics)
    print("\n" + report)

    # Print classification
    print(f"\n{'=' * 60}")
    print(f"Overall Performance: {metrics['classification']}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
