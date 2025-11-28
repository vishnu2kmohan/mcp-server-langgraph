#!/usr/bin/env python3
"""
Generate ASCII TODO burndown chart from git history.

This script analyzes git commit history to track TODO resolution over time
and generates visual burndown charts.

Usage:
    python scripts/workflow/generate-burndown.py --days 30
    python scripts/workflow/generate-burndown.py --days 14 --output burndown.txt
    python scripts/workflow/generate-burndown.py --from-date 2025-10-01

Features:
- ASCII chart visualization
- Velocity calculation
- Trend analysis
- Projected completion date
- Historical TODO tracking per commit
"""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def run_git_command(args: list[str], timeout: int = 30) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Git command failed: {e}", file=sys.stderr)
        return ""


def count_todos_at_commit(commit_hash: str) -> int:
    """Count TODOs in source code at a specific commit."""
    try:
        # Get all Python files in src/
        files_output = run_git_command(
            [
                "ls-tree",
                "-r",
                "--name-only",
                commit_hash,
                "src/",
            ]
        )

        if not files_output:
            return 0

        files = [f for f in files_output.split("\n") if f.endswith(".py")]

        total_todos = 0
        for file_path in files:
            try:
                content = run_git_command(["show", f"{commit_hash}:{file_path}"])
                total_todos += content.count("TODO")
            except Exception:
                continue

        return total_todos

    except Exception as e:
        print(f"WARNING: Could not count TODOs at {commit_hash[:7]}: {e}", file=sys.stderr)
        return 0


def get_todo_history(days: int = 30) -> list[tuple[str, int, str]]:
    """Get TODO counts over time from git history."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Get commits in date range
    log_output = run_git_command(
        [
            "log",
            f"--since={since_date}",
            "--format=%H|%ad|%s",
            "--date=short",
            "--reverse",  # Oldest first
        ]
    )

    if not log_output:
        return []

    history = []
    for line in log_output.split("\n"):
        if not line:
            continue

        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        commit_hash, date, message = parts

        # Sample every few commits for performance (full scan is slow)
        # For 30 days, sample ~10-15 commits
        if len(history) > 0 and len(history) % 3 != 0:
            continue  # Skip some commits

        todo_count = count_todos_at_commit(commit_hash)
        history.append((date, todo_count, message))

    # Always include latest commit
    latest_hash = run_git_command(["rev-parse", "HEAD"])
    latest_date = datetime.now().strftime("%Y-%m-%d")
    latest_count = count_todos_at_commit(latest_hash)
    history.append((latest_date, latest_count, "Current"))

    return history


def calculate_velocity(history: list[tuple[str, int, str]], days: int = 7) -> float:
    """Calculate TODO resolution velocity (TODOs/day)."""
    if len(history) < 2:
        return 0.0

    # Get data points within last N days
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_data = [(d, c) for d, c, _ in history if d >= cutoff_date]

    if len(recent_data) < 2:
        recent_data = [(d, c) for d, c, _ in history[-7:]]  # Fallback to last 7 points

    if len(recent_data) < 2:
        return 0.0

    # Calculate average daily change
    start_date, start_count = recent_data[0]
    end_date, end_count = recent_data[-1]

    date_diff = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days

    if date_diff == 0:
        return 0.0

    velocity = (start_count - end_count) / date_diff  # Positive = resolving TODOs
    return velocity


def draw_burndown_chart(history: list[tuple[str, int, str]], width: int = 40, height: int = 10) -> str:
    """Draw ASCII burndown chart."""
    if not history or len(history) < 2:
        return "Not enough data for chart (need at least 2 data points)"

    dates = [d for d, _, _ in history]
    counts = [c for _, c, _ in history]

    max_count = max(counts) if counts else 0
    min_count = min(counts) if counts else 0

    if max_count == min_count:
        max_count += 10  # Avoid division by zero

    # Build chart
    chart_lines = []

    # Y-axis labels and data
    for y in range(height, -1, -1):
        value = int(min_count + (max_count - min_count) * y / height)

        # Y-axis label
        line = f"{value:3d} │"

        # Plot points
        for i, (date, count, _) in enumerate(history):
            x_pos = int(i * width / (len(history) - 1))  # noqa: F841

            # Calculate Y position for this count
            y_pos = int((count - min_count) / (max_count - min_count) * height)

            if y_pos == y:
                line += "●"
            else:
                line += " "

        chart_lines.append(line)

    # X-axis
    x_axis = "    └" + "─" * width
    chart_lines.append(x_axis)

    # X-axis labels (dates)
    first_date = dates[0]
    mid_date = dates[len(dates) // 2] if len(dates) > 2 else ""
    last_date = dates[-1]

    date_line = f"     {first_date:10s}"
    if mid_date:
        date_line += f" {mid_date:10s}"
    date_line += f" {last_date:10s}"
    chart_lines.append(date_line)

    return "\n".join(chart_lines)


def generate_report(history: list[tuple[str, int, str]], days: int) -> str:
    """Generate full TODO burndown report."""
    if not history:
        return "No TODO history available"

    current_count = history[-1][1]
    start_count = history[0][1]
    resolved = start_count - current_count

    velocity_7 = calculate_velocity(history, 7)
    velocity_14 = calculate_velocity(history, 14)
    velocity_30 = calculate_velocity(history, 30)

    # Projected completion
    if velocity_7 > 0:
        days_to_complete = current_count / velocity_7
        completion_date = datetime.now() + timedelta(days=days_to_complete)
        completion_str = completion_date.strftime("%Y-%m-%d")
    else:
        completion_str = "Unknown (no resolution activity)"
        days_to_complete = 0

    # Build report
    report = f"""
# TODO Burndown Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Time Range**: Last {days} days
**Data Points**: {len(history)} commits sampled

---

## 📊 Overview

| Metric | Value |
|--------|-------|
| Current TODOs | {current_count} |
| Started With | {start_count} |
| Resolved | {resolved} ({resolved / start_count * 100:.1f}%) |
| Net Change | {current_count - start_count:+d} |

---

## 📉 Burndown Chart

```
{draw_burndown_chart(history)}
```

Legend:
● Actual data points

---

## ⚡ Velocity Analysis

| Period | Velocity | Trend |
|--------|----------|-------|
| Last 7 days | {velocity_7:.2f} TODOs/day | {"↑ Accelerating" if velocity_7 > velocity_14 else "↓ Slowing"} |
| Last 14 days | {velocity_14:.2f} TODOs/day | {"↑ Above avg" if velocity_14 > velocity_30 else "↓ Below avg"} |
| Last 30 days | {velocity_30:.2f} TODOs/day | - |

---

## 🎯 Projections

At current velocity ({velocity_7:.2f} TODOs/day):
- **Days to completion**: {days_to_complete:.1f} days
- **Projected date**: {completion_str}
- **Remaining work**: {current_count} TODOs

---

## 📅 Historical Data

| Date | TODOs | Change | Event |
|------|-------|--------|-------|
"""

    for i, (date, count, msg) in enumerate(history[-10:]):  # Last 10 points
        if i > 0:
            prev_count = history[i - 1][1]
            change = count - prev_count
            change_str = f"{change:+d}"
        else:
            change_str = "-"

        # Truncate message
        msg_short = (msg[:40] + "...") if len(msg) > 40 else msg
        report += f"| {date} | {count} | {change_str} | {msg_short} |\n"

    report += """

---

## 💡 Insights

"""

    # Add insights
    if resolved > 0:
        report += f"- ✅ **Great progress!** Resolved {resolved} TODOs ({resolved / start_count * 100:.1f}%)\n"

    if velocity_7 > velocity_14:
        report += f"- 📈 **Accelerating** - velocity increased from {velocity_14:.2f} to {velocity_7:.2f} TODOs/day\n"
    elif velocity_7 < velocity_14:
        report += f"- 📉 **Slowing down** - velocity decreased from {velocity_14:.2f} to {velocity_7:.2f} TODOs/day\n"

    if current_count < 10:
        report += f"- 🎯 **Almost done!** Only {current_count} TODOs remaining\n"

    if velocity_7 > 1.0:
        report += f"- ⚡ **High velocity** - resolving {velocity_7:.2f} TODOs per day\n"

    report += """

---

**Generated by**: `scripts/workflow/generate-burndown.py`
**Data source**: Git commit history
**Accuracy**: Sampled data (every ~3 commits for performance)
"""

    return report


def main():
    parser = argparse.ArgumentParser(description="Generate TODO burndown chart")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--output", type=str, help="Output file (default: stdout)")
    parser.add_argument("--from-date", type=str, help="Start date (YYYY-MM-DD)")

    args = parser.parse_args()

    print(f"🔄 Analyzing TODO history ({args.days} days)...", file=sys.stderr)
    print("⏳ This may take a moment (scanning git commits)...", file=sys.stderr)

    # Get TODO history
    history = get_todo_history(args.days)

    if not history:
        print("ERROR: No TODO history found", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Analyzed {len(history)} commits", file=sys.stderr)

    # Generate report
    report = generate_report(history, args.days)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report)
        print(f"✅ Report written to: {output_path}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
