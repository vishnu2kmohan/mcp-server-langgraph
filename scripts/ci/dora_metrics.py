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
from typing import Dict, List, Optional, Tuple


def run_gh_command(args: List[str]) -> str:
    """Run gh CLI command and return output."""
    try:
        result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def calculate_deployment_frequency(repo: str, days: int) -> Tuple[float, str]:
    """Calculate deployment frequency (deployments per day)."""
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
    df_value, df_class = calculate_deployment_frequency(args.repo, args.days)
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
