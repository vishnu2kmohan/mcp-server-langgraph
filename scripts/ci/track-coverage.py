#!/usr/bin/env python3
"""
Coverage Trend Tracker

Tracks and analyzes test coverage trends over time.
Extracted from .github/workflows/coverage-trend.yaml for maintainability.

Usage:
    python scripts/ci/track-coverage.py [--coverage-json PATH] [--history-dir PATH]

Example:
    python scripts/ci/track-coverage.py --coverage-json coverage.json --history-dir .coverage-history

Exit codes:
    0 - Coverage acceptable
    1 - Coverage dropped significantly (>5%)
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def extract_coverage_percentage(coverage_json_path):
    """Extract coverage percentage from coverage.json"""
    try:
        with open(coverage_json_path, "r") as f:
            data = json.load(f)
        coverage = data["totals"]["percent_covered"]
        return round(coverage, 1)
    except Exception as e:
        print(f"❌ Error reading coverage JSON: {e}")
        sys.exit(1)


def get_commit_info():
    """Get current commit SHA"""
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def save_coverage_to_history(coverage, history_dir):
    """Save current coverage to history"""
    history_path = Path(history_dir)
    history_path.mkdir(parents=True, exist_ok=True)

    history_file = history_path / "coverage-trend.csv"

    date = datetime.now().strftime("%Y-%m-%d")
    commit_sha = get_commit_info()
    entry = f"{date},{commit_sha},{coverage}\n"

    # Append to history
    with open(history_file, "a") as f:
        f.write(entry)

    # Keep only last 100 entries
    with open(history_file, "r") as f:
        lines = f.readlines()

    if len(lines) > 100:
        with open(history_file, "w") as f:
            f.writelines(lines[-100:])

    print(f"📊 Coverage saved to history: {history_file}")


def get_previous_coverage(history_dir):
    """Get previous coverage from history"""
    history_file = Path(history_dir) / "coverage-trend.csv"

    if not history_file.exists():
        return None

    with open(history_file, "r") as f:
        lines = f.readlines()

    if len(lines) < 2:
        return None

    # Get second to last line (previous entry)
    prev_line = lines[-2].strip()
    parts = prev_line.split(",")

    if len(parts) >= 3:
        return float(parts[2])

    return None


def analyze_coverage_change(current, previous):
    """Analyze coverage change and determine status"""
    if previous is None:
        return {"change": "N/A", "status": "📊 First measurement", "alert": False}

    change = round(current - previous, 1)

    if change < -5:
        status = "🔴 Significant decrease"
        alert = True
    elif change < -1:
        status = "🟡 Decrease"
        alert = False
    elif change > 1:
        status = "🟢 Increase"
        alert = False
    else:
        status = "➡️  No change"
        alert = False

    return {"change": change, "status": status, "alert": alert}


def main():
    parser = argparse.ArgumentParser(description="Track coverage trends")
    parser.add_argument("--coverage-json", default="coverage.json", help="Path to coverage.json file (default: coverage.json)")
    parser.add_argument(
        "--history-dir", default=".coverage-history", help="Directory to store coverage history (default: .coverage-history)"
    )
    parser.add_argument(
        "--fail-threshold", type=float, default=5.0, help="Fail if coverage drops by more than this percentage (default: 5.0)"
    )

    args = parser.parse_args()

    # Extract current coverage
    coverage = extract_coverage_percentage(args.coverage_json)
    print(f"📊 Current coverage: {coverage}%")

    # Get previous coverage
    previous_coverage = get_previous_coverage(args.history_dir)

    if previous_coverage is not None:
        print(f"📊 Previous coverage: {previous_coverage}%")

    # Save current coverage to history
    save_coverage_to_history(coverage, args.history_dir)

    # Analyze change
    analysis = analyze_coverage_change(coverage, previous_coverage)

    print(f"\n{analysis['status']}")

    if analysis["change"] != "N/A":
        print(f"Change: {analysis['change']:+.1f}%")

    # Check alert condition
    if analysis["alert"]:
        print(f"\n⚠️  Coverage dropped by more than {args.fail_threshold}%!")
        print(f"Previous: {previous_coverage}%")
        print(f"Current: {coverage}%")
        print(f"Change: {analysis['change']:+.1f}%")
        sys.exit(1)

    print("\n✅ Coverage check passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
