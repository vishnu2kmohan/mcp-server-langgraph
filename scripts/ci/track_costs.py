#!/usr/bin/env python3
"""
GitHub Actions Cost Tracking Script

Analyzes GitHub Actions workflow runs to track usage, estimate costs,
and identify optimization opportunities.

Budget Targets:
  - Monthly: <6000 minutes (~$48/month)
  - Weekly: <1500 minutes (~$12/week)

Usage:
    PERIOD_DAYS=7 python track-costs.py

Environment Variables:
    PERIOD_DAYS: Number of days to analyze (default: 7)

Input Files:
    workflow-runs.json: First page of workflow runs from GitHub API
    workflow-runs-page2.json: Second page (optional)

Output Files:
    cost-report.md: Markdown report with analysis
    cost-metrics.txt: Key metrics in key=value format
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List


# Cost per minute for public repos (GitHub Actions pricing)
COST_PER_MIN_LINUX = 0.008  # $0.008/min for Linux runners

# Budget thresholds
WEEKLY_BUDGET_MINS = 1500  # ~$12/week
MONTHLY_BUDGET_MINS = 6000  # ~$48/month


def load_runs() -> list[dict[str, Any]]:
    """
    Load workflow runs from JSON files.

    Reads workflow-runs.json and workflow-runs-page2.json (if present)
    and combines the workflow_runs arrays.

    Returns:
        List of workflow run dictionaries
    """
    runs = []

    try:
        with open("workflow-runs.json") as f:
            data = json.load(f)
            runs.extend(data.get("workflow_runs", []))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    try:
        with open("workflow-runs-page2.json") as f:
            data = json.load(f)
            runs.extend(data.get("workflow_runs", []))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return runs


def analyze_usage(runs: list[dict[str, Any]], period_days: int) -> str:
    """
    Analyze workflow usage and costs.

    Args:
        runs: List of workflow run dictionaries
        period_days: Number of days in the analysis period

    Returns:
        Markdown-formatted report string
    """
    by_workflow = defaultdict(lambda: {"count": 0, "total_minutes": 0, "billable_minutes": 0})
    total_minutes = 0.0
    total_billable = 0

    for run in runs:
        workflow_name = run.get("name", "Unknown")

        # Duration in minutes (run_duration_ms is in milliseconds)
        duration_ms = run.get("run_duration_ms", 0)
        duration_min = duration_ms / 1000 / 60 if duration_ms else 0

        # Billable time (rounded up to nearest minute)
        billable = int(duration_min) + (1 if duration_min % 1 > 0 else 0)

        by_workflow[workflow_name]["count"] += 1
        by_workflow[workflow_name]["total_minutes"] += duration_min
        by_workflow[workflow_name]["billable_minutes"] += billable

        total_minutes += duration_min
        total_billable += billable

    # Calculate costs
    total_cost = total_billable * COST_PER_MIN_LINUX

    # Budget status
    if period_days <= 7:
        budget = WEEKLY_BUDGET_MINS
        budget_name = "Weekly"
    else:
        budget = MONTHLY_BUDGET_MINS
        budget_name = "Monthly"

    budget_pct = (total_billable / budget * 100) if budget > 0 else 0
    budget_remaining = budget - total_billable

    # Generate report
    report = []
    report.append(f"# GitHub Actions Cost Report ({period_days} days)")
    report.append("")
    report.append(f"**Period:** Last {period_days} days")
    report.append(f"**Total Runs:** {len(runs)}")
    report.append(f"**Total Minutes:** {total_minutes:.1f} min ({total_billable} billable)")
    report.append(f"**Estimated Cost:** ${total_cost:.2f}")
    report.append("")

    # Budget status
    status_emoji = "✅" if budget_pct < 80 else ("🟡" if budget_pct < 100 else "🔴")
    report.append(f"## {status_emoji} {budget_name} Budget Status")
    report.append("")
    report.append(f"- **Budget:** {budget} minutes (${budget * COST_PER_MIN_LINUX:.2f})")
    report.append(f"- **Used:** {total_billable} minutes (${total_cost:.2f})")
    report.append(f"- **Remaining:** {budget_remaining} minutes (${budget_remaining * COST_PER_MIN_LINUX:.2f})")
    report.append(f"- **Utilization:** {budget_pct:.1f}%")
    report.append("")

    # Top workflows by cost
    report.append("## Top Workflows by Cost")
    report.append("")
    report.append("| Workflow | Runs | Total Min | Billable Min | Cost |")
    report.append("|----------|------|-----------|--------------|------|")

    sorted_workflows = sorted(by_workflow.items(), key=lambda x: x[1]["billable_minutes"], reverse=True)

    for workflow_name, stats in sorted_workflows[:10]:
        cost = stats["billable_minutes"] * COST_PER_MIN_LINUX
        report.append(
            f"| {workflow_name} | {stats['count']} | {stats['total_minutes']:.1f} | {stats['billable_minutes']} | ${cost:.2f} |"
        )

    # Optimization recommendations
    report.append("")
    report.append("## 💡 Optimization Opportunities")
    report.append("")

    # Find workflows with high average duration
    high_duration = [
        (name, stats)
        for name, stats in by_workflow.items()
        if stats["count"] > 0 and stats["total_minutes"] / stats["count"] > 15
    ]

    if high_duration:
        report.append("### High Duration Workflows (>15 min avg)")
        for name, stats in sorted(high_duration, key=lambda x: x[1]["total_minutes"] / x[1]["count"], reverse=True)[:5]:
            avg = stats["total_minutes"] / stats["count"]
            report.append(f"- **{name}**: {avg:.1f} min avg ({stats['count']} runs)")

    # High frequency workflows
    high_freq = [(name, stats) for name, stats in by_workflow.items() if stats["count"] > 20]
    if high_freq:
        report.append("")
        report.append("### High Frequency Workflows (>20 runs)")
        for name, stats in sorted(high_freq, key=lambda x: x[1]["count"], reverse=True)[:5]:
            report.append(f"- **{name}**: {stats['count']} runs")

    # Save metrics
    with open("cost-metrics.txt", "w") as f:
        f.write(f"total_minutes={total_minutes:.1f}\n")
        f.write(f"billable_minutes={total_billable}\n")
        f.write(f"total_cost={total_cost:.2f}\n")
        f.write(f"budget_pct={budget_pct:.1f}\n")
        f.write(f"budget_remaining={budget_remaining}\n")

    # Save report
    with open("cost-report.md", "w") as f:
        f.write("\n".join(report))

    return "\n".join(report)


def main() -> None:
    """
    Main execution function.

    Reads workflow runs, analyzes costs, and generates reports.
    """
    # Get period from environment variable
    period_days = int(os.environ.get("PERIOD_DAYS", 7))

    # Load workflow runs
    runs = load_runs()

    # Analyze and generate report
    report = analyze_usage(runs, period_days)

    # Print report to stdout
    print(report)


if __name__ == "__main__":
    main()
