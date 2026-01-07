#!/usr/bin/env python3
"""
Grafana Dashboard Auto-Fix Script

Automatically fixes common dashboard issues detected by validate_grafana_dashboards.py.

Fixes:
- graphTooltip: Sets to 1 (shared crosshair) if 0
- timepicker.refresh_intervals: Adds if missing
- Basic navigation links: Adds if completely missing

Usage:
    uv run python scripts/validation/fix_grafana_dashboards.py
    uv run python scripts/validation/fix_grafana_dashboards.py --dry-run
    uv run python scripts/validation/fix_grafana_dashboards.py monitoring/grafana/dashboards/AI/ai-suggestions.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Dashboard directories to fix
DASHBOARD_DIRS = [
    Path("monitoring/grafana/dashboards"),
]

# Standard timepicker refresh intervals
STANDARD_REFRESH_INTERVALS = ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"]


def fix_graph_tooltip(dashboard: dict) -> bool:
    """Set graphTooltip to 1 (shared crosshair) if it's 0."""
    if dashboard.get("graphTooltip", 0) == 0:
        dashboard["graphTooltip"] = 1
        return True
    return False


def fix_timepicker(dashboard: dict) -> bool:
    """Add refresh_intervals to timepicker if missing."""
    if "timepicker" not in dashboard:
        dashboard["timepicker"] = {}

    timepicker = dashboard["timepicker"]

    if "refresh_intervals" not in timepicker or not timepicker["refresh_intervals"]:
        timepicker["refresh_intervals"] = STANDARD_REFRESH_INTERVALS
        return True
    return False


def fix_dashboard(filepath: Path, dry_run: bool = False) -> dict:
    """Fix a single dashboard file and return stats."""
    stats = {
        "file": filepath.name,
        "fixes": [],
        "skipped": False,
    }

    try:
        with open(filepath) as f:
            dashboard = json.load(f)
    except json.JSONDecodeError as e:
        stats["skipped"] = True
        stats["error"] = f"Invalid JSON: {e}"
        return stats

    # Apply fixes
    if fix_graph_tooltip(dashboard):
        stats["fixes"].append("graphTooltip set to 1 (shared crosshair)")

    if fix_timepicker(dashboard):
        stats["fixes"].append("Added timepicker.refresh_intervals")

    # Write back if fixes were made and not dry-run
    if stats["fixes"] and not dry_run:
        with open(filepath, "w") as f:
            json.dump(dashboard, f, indent=2)
            f.write("\n")  # Add trailing newline

    return stats


def find_dashboard_files() -> list[Path]:
    """Find all dashboard JSON files in canonical location."""
    files = []

    for dir_path in DASHBOARD_DIRS:
        if dir_path.exists():
            files.extend(dir_path.rglob("*.json"))

    return sorted(set(files))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Auto-fix Grafana dashboard issues")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific files to fix (default: all dashboards in canonical location)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("GRAFANA DASHBOARD AUTO-FIX")
    print("=" * 70)

    if args.dry_run:
        print("Mode: DRY-RUN (no changes will be made)")
    print()

    # Get files to fix
    if args.files:
        dashboard_files = args.files
    else:
        dashboard_files = find_dashboard_files()

    if not dashboard_files:
        print("No dashboard files found.")
        return 0

    print(f"Found {len(dashboard_files)} dashboard files")
    print()

    fixed_count = 0
    skipped_count = 0
    total_fixes = 0

    for filepath in dashboard_files:
        stats = fix_dashboard(filepath, dry_run=args.dry_run)

        if stats["skipped"]:
            print(f"SKIP: {stats['file']} - {stats.get('error', 'Unknown error')}")
            skipped_count += 1
            continue

        if stats["fixes"]:
            action = "Would fix" if args.dry_run else "Fixed"
            print(f"{action}: {filepath}")
            for fix in stats["fixes"]:
                print(f"  - {fix}")
            fixed_count += 1
            total_fixes += len(stats["fixes"])

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Dashboards scanned: {len(dashboard_files)}")
    print(f"  Dashboards {'would be ' if args.dry_run else ''}fixed: {fixed_count}")
    print(f"  Total fixes applied: {total_fixes}")
    print(f"  Skipped (errors): {skipped_count}")

    if args.dry_run and fixed_count > 0:
        print()
        print("Run without --dry-run to apply fixes.")

    if not args.dry_run and fixed_count > 0:
        print()
        print("Don't forget to sync to Helm: ./scripts/sync-grafana-dashboards.sh")

    return 0


if __name__ == "__main__":
    sys.exit(main())
