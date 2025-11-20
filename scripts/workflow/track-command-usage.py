#!/usr/bin/env python3
"""
Track Claude Code command usage and measure time savings.

This script:
1. Logs command usage with timestamps
2. Calculates actual time savings
3. Generates usage analytics
4. Measures ROI

Usage:
    python scripts/workflow/track-command-usage.py --log "/quick-debug"
    python scripts/workflow/track-command-usage.py --report
    python scripts/workflow/track-command-usage.py --roi
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# Time savings estimates (in minutes) for each command
COMMAND_SAVINGS = {
    # Existing commands (v2.0)
    "/quick-debug": 12,  # 20min → 8min = 12min saved
    "/test-summary": 5,  # 10min → 5min = 5min saved
    "/test-failure-analysis": 15,  # 25min → 10min = 15min saved
    "/ci-status": 4.5,  # 5min → 0.5min = 4.5min saved
    "/pr-checks": 10,  # 15min → 5min = 10min saved
    "/start-sprint": 20,  # 30min → 10min = 20min saved
    "/progress-update": 20,  # 30min → 10min = 20min saved
    "/todo-status": 15,  # 20min → 5min = 15min saved
    "/release-prep": 30,  # 45min → 15min = 30min saved
    "/benchmark": 5,  # 10min → 5min = 5min saved (running time, not analysis)
    "/security-scan-report": 10,  # 15min → 5min = 10min saved
    "/docs-audit": 25,  # 40min → 15min = 25min saved
    "/fix-issue": 20,  # 30min → 10min = 20min saved
    "/debug-auth": 15,  # 25min → 10min = 15min saved
    "/deploy-dev": 10,  # 15min → 5min = 10min saved
    "/lint": 3,  # 5min → 2min = 3min saved
    "/validate": 10,  # 15min → 5min = 10min saved
    "/test-all": 0,  # No savings, just runs tests
    "/test-fast": 0,  # No savings, just runs tests
    "/refresh-context": 9,  # 10min → 1min = 9min saved
    "/coverage-trend": 10,  # 15min → 5min = 10min saved
    # New commands (v3.0)
    "/create-adr": 40,  # 60min → 20min = 40min saved
    "/create-test": 18,  # 25min → 7min = 18min saved
    "/improve-coverage": 45,  # 60min → 15min = 45min saved
    "/coverage-gaps": 20,  # 30min → 10min = 20min saved
    "/type-safety-status": 15,  # 25min → 10min = 15min saved
    "/deploy": 25,  # 40min → 15min = 25min saved
    "/knowledge-search": 10,  # 15min → 5min = 10min saved
}


class CommandTracker:
    """Track command usage and calculate time savings."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.claude_dir = repo_root / ".claude"
        self.analytics_dir = self.claude_dir / "analytics"
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

        self.usage_log = self.analytics_dir / "command-usage.jsonl"
        self.summary_file = self.analytics_dir / "usage-summary.json"

    def log_command(self, command: str, duration_seconds: int | None = None):
        """Log a command usage."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "duration_seconds": duration_seconds,
            "estimated_savings_minutes": COMMAND_SAVINGS.get(command, 0),
        }

        # Append to JSONL log
        with open(self.usage_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"✅ Logged: {command} (saves ~{COMMAND_SAVINGS.get(command, 0)} min)")

    def load_usage_log(self) -> list[dict]:
        """Load all usage entries."""
        if not self.usage_log.exists():
            return []

        entries = []
        with open(self.usage_log) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def generate_report(self, days: int = 30) -> dict:
        """Generate usage report for last N days."""
        entries = self.load_usage_log()
        cutoff = datetime.now() - timedelta(days=days)

        # Filter by date
        recent_entries = [e for e in entries if datetime.fromisoformat(e["timestamp"]) > cutoff]

        if not recent_entries:
            return {"error": "No usage data found"}

        # Calculate statistics
        command_counts = {}
        command_savings = {}
        total_uses = len(recent_entries)
        total_savings = 0

        for entry in recent_entries:
            cmd = entry["command"]
            savings = entry.get("estimated_savings_minutes", 0)

            command_counts[cmd] = command_counts.get(cmd, 0) + 1
            command_savings[cmd] = command_savings.get(cmd, 0) + savings
            total_savings += savings

        # Sort by usage
        top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)

        # Calculate per-sprint statistics (assuming 2-week sprints)
        sprints = days / 14
        avg_savings_per_sprint = total_savings / sprints if sprints > 0 else 0

        report = {
            "period_days": days,
            "period_start": cutoff.isoformat(),
            "period_end": datetime.now().isoformat(),
            "total_command_uses": total_uses,
            "unique_commands": len(command_counts),
            "total_time_saved_minutes": total_savings,
            "total_time_saved_hours": total_savings / 60,
            "avg_savings_per_sprint_hours": avg_savings_per_sprint / 60,
            "top_commands": [
                {
                    "command": cmd,
                    "uses": count,
                    "total_savings_minutes": command_savings.get(cmd, 0),
                    "total_savings_hours": command_savings.get(cmd, 0) / 60,
                    "avg_savings_per_use": command_savings.get(cmd, 0) / count,
                }
                for cmd, count in top_commands[:10]
            ],
            "all_commands": command_counts,
        }

        # Save summary
        with open(self.summary_file, "w") as f:
            json.dumps(report, f, indent=2)

        return report

    def calculate_roi(self) -> dict:
        """Calculate ROI of workflow optimization."""
        entries = self.load_usage_log()

        if not entries:
            return {"error": "No usage data found"}

        # Calculate total savings
        total_savings_minutes = sum(e.get("estimated_savings_minutes", 0) for e in entries)
        total_savings_hours = total_savings_minutes / 60

        # Investment (from workflow optimization)
        initial_investment_hours = 15  # Original v2.0 implementation
        v3_investment_hours = 20  # v3.0 enhancements
        total_investment_hours = initial_investment_hours + v3_investment_hours

        # ROI calculation
        roi_multiplier = total_savings_hours / total_investment_hours if total_investment_hours > 0 else 0
        roi_percentage = (roi_multiplier - 1) * 100

        # Annualized projections
        days_of_data = (datetime.now() - datetime.fromisoformat(entries[0]["timestamp"])).days

        if days_of_data > 0:
            annual_savings_hours = (total_savings_hours / days_of_data) * 365
            work_weeks_saved = annual_savings_hours / 40
        else:
            annual_savings_hours = 0
            work_weeks_saved = 0

        return {
            "total_command_uses": len(entries),
            "total_savings_hours": total_savings_hours,
            "investment_hours": total_investment_hours,
            "roi_multiplier": roi_multiplier,
            "roi_percentage": roi_percentage,
            "days_of_data": days_of_data,
            "annual_projected_savings_hours": annual_savings_hours,
            "annual_work_weeks_saved": work_weeks_saved,
            "break_even_status": "Achieved" if roi_multiplier >= 1 else "Not Yet",
        }

    def print_report(self, days: int = 30):
        """Print formatted usage report."""
        report = self.generate_report(days)

        if "error" in report:
            print(f"❌ {report['error']}")
            return

        print("━" * 70)
        print("  COMMAND USAGE REPORT")
        print("━" * 70)
        print()
        print(f"  Period: Last {days} days")
        print(f"  From: {report['period_start'][:10]} to {report['period_end'][:10]}")
        print()
        print(f"  Total Commands Used: {report['total_command_uses']}")
        print(f"  Unique Commands: {report['unique_commands']}")
        print(f"  Total Time Saved: {report['total_time_saved_hours']:.1f} hours")
        print(f"  Avg Savings/Sprint: {report['avg_savings_per_sprint_hours']:.1f} hours")
        print()
        print("  Top 10 Commands:")
        print("  " + "─" * 66)
        print(f"  {'Command':<30} {'Uses':<8} {'Saved':<12} {'Avg/Use':<10}")
        print("  " + "─" * 66)

        for cmd_data in report["top_commands"]:
            cmd = cmd_data["command"]
            uses = cmd_data["uses"]
            saved = cmd_data["total_savings_hours"]
            avg = cmd_data["avg_savings_per_use"]
            print(f"  {cmd:<30} {uses:<8} {saved:>6.1f}h      {avg:>6.1f}min")

        print("  " + "─" * 66)
        print()

    def print_roi(self):
        """Print formatted ROI report."""
        roi = self.calculate_roi()

        if "error" in roi:
            print(f"❌ {roi['error']}")
            return

        print("━" * 70)
        print("  WORKFLOW OPTIMIZATION ROI")
        print("━" * 70)
        print()
        print(f"  Total Command Uses: {roi['total_command_uses']}")
        print(f"  Total Time Saved: {roi['total_savings_hours']:.1f} hours")
        print(f"  Investment: {roi['investment_hours']} hours")
        print()
        print(f"  ROI: {roi['roi_multiplier']:.1f}x ({roi['roi_percentage']:+.0f}%)")
        print(f"  Break-Even: {roi['break_even_status']}")
        print()
        print(f"  Data Collection: {roi['days_of_data']} days")
        print(f"  Projected Annual Savings: {roi['annual_projected_savings_hours']:.0f} hours")
        print(f"  Equivalent Work Weeks: {roi['annual_work_weeks_saved']:.1f} weeks")
        print()
        print("━" * 70)

        # Visual representation
        if roi["roi_multiplier"] >= 1:
            bar_length = min(int(roi["roi_multiplier"] * 2), 50)
            bar = "█" * bar_length
            print(f"  Return: {bar} {roi['roi_multiplier']:.1f}x")
            print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Track command usage and measure time savings")
    parser.add_argument(
        "--log",
        type=str,
        help="Log a command usage (e.g., '/quick-debug')",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Command duration in seconds (optional)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate usage report",
    )
    parser.add_argument(
        "--roi",
        action="store_true",
        help="Calculate ROI",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days for report (default: 30)",
    )

    args = parser.parse_args()

    # Find repo root
    repo_root = Path.cwd()
    while not (repo_root / ".git").exists() and repo_root != repo_root.parent:
        repo_root = repo_root.parent

    if not (repo_root / ".git").exists():
        print("Error: Not in a git repository")
        return 1

    tracker = CommandTracker(repo_root)

    if args.log:
        tracker.log_command(args.log, args.duration)
    elif args.report:
        tracker.print_report(args.days)
    elif args.roi:
        tracker.print_roi()
    else:
        print("Use --log, --report, or --roi")
        print("Example: python track-command-usage.py --log '/quick-debug'")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
