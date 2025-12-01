#!/usr/bin/env python3
"""
Cleanup old telemetry data to enforce retention policy.

This script prunes telemetry data files to:
- Filter data older than 90 days
- Cap at 500 runs maximum

Usage:
    python cleanup_telemetry.py --trends-dir gh-pages/trends --max-age-days 90 --max-runs 500

This prevents gh-pages from exceeding the 1GB storage limit.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp string to datetime.

    Args:
        timestamp_str: ISO 8601 formatted timestamp string

    Returns:
        Parsed datetime object (UTC)
    """
    # Handle various ISO 8601 formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            continue

    # Fallback: try fromisoformat (Python 3.11+)
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt
    except ValueError as e:
        raise ValueError(f"Unable to parse timestamp: {timestamp_str}") from e


def cleanup_trends_file(
    file_path: Path,
    max_age_days: int = 90,
    max_runs: int = 500,
    dry_run: bool = False,
) -> dict[str, int]:
    """Clean up a trends JSON file according to retention policy.

    Args:
        file_path: Path to the JSON file
        max_age_days: Maximum age in days to retain
        max_runs: Maximum number of runs to retain
        dry_run: If True, don't modify files

    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "original_count": 0,
        "after_date_filter": 0,
        "after_run_cap": 0,
        "removed_count": 0,
    }

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return stats

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.exception(f"Invalid JSON in {file_path}: {e}")
        return stats

    # Handle different data structures
    if isinstance(data, dict) and "runs" in data:
        runs = data["runs"]
    elif isinstance(data, list):
        runs = data
    else:
        logger.warning(f"Unexpected data structure in {file_path}")
        return stats

    stats["original_count"] = len(runs)

    if not runs:
        logger.info(f"No runs in {file_path}")
        return stats

    # Calculate cutoff date
    cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
    logger.info(f"Cutoff date: {cutoff_date.isoformat()}")

    # Filter by date
    filtered_runs = []
    for run in runs:
        # Try to find timestamp field
        timestamp_str = run.get("timestamp") or run.get("date") or run.get("created_at")
        if not timestamp_str:
            # Keep runs without timestamp (to be safe)
            filtered_runs.append(run)
            continue

        try:
            run_date = parse_timestamp(timestamp_str)
            if run_date > cutoff_date:
                filtered_runs.append(run)
        except ValueError as e:
            logger.warning(f"Could not parse timestamp: {e}")
            # Keep runs with unparseable timestamps
            filtered_runs.append(run)

    stats["after_date_filter"] = len(filtered_runs)

    # Cap at max_runs (keep most recent)
    if len(filtered_runs) > max_runs:
        # Sort by timestamp (most recent first) and take max_runs
        try:
            filtered_runs.sort(
                key=lambda r: parse_timestamp(
                    r.get("timestamp") or r.get("date") or r.get("created_at") or "1970-01-01T00:00:00Z"
                ),
                reverse=True,
            )
        except (ValueError, TypeError):
            # If sorting fails, just take the last max_runs (assume chronological order)
            pass
        filtered_runs = filtered_runs[:max_runs]

    stats["after_run_cap"] = len(filtered_runs)
    stats["removed_count"] = stats["original_count"] - stats["after_run_cap"]

    # Write back if changes were made
    if stats["removed_count"] > 0:
        if dry_run:
            logger.info(f"[DRY RUN] Would remove {stats['removed_count']} runs from {file_path}")
        else:
            # Reconstruct data structure
            if isinstance(data, dict) and "runs" in data:
                data["runs"] = filtered_runs
            else:
                data = filtered_runs

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Removed {stats['removed_count']} runs from {file_path}")
    else:
        logger.info(f"No cleanup needed for {file_path}")

    return stats


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup old telemetry data to enforce retention policy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--trends-dir",
        type=Path,
        required=True,
        help="Directory containing trends JSON files",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Maximum age in days to retain (default: 90)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=500,
        help="Maximum number of runs to retain (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Telemetry Cleanup")
    logger.info("=" * 60)
    logger.info(f"Trends directory: {args.trends_dir}")
    logger.info(f"Retention policy: {args.max_age_days} days / {args.max_runs} runs")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")

    if not args.trends_dir.exists():
        logger.warning(f"Trends directory not found: {args.trends_dir}")
        return 0

    # Find all JSON files in trends directory
    json_files = list(args.trends_dir.glob("*.json"))
    if not json_files:
        logger.info("No JSON files found in trends directory")
        return 0

    logger.info(f"Found {len(json_files)} JSON files")

    total_stats = {
        "files_processed": 0,
        "total_removed": 0,
    }

    for json_file in json_files:
        logger.info(f"\nProcessing: {json_file.name}")
        stats = cleanup_trends_file(
            json_file,
            max_age_days=args.max_age_days,
            max_runs=args.max_runs,
            dry_run=args.dry_run,
        )
        total_stats["files_processed"] += 1
        total_stats["total_removed"] += stats["removed_count"]

        logger.debug(
            f"  Original: {stats['original_count']}, "
            f"After date filter: {stats['after_date_filter']}, "
            f"After run cap: {stats['after_run_cap']}"
        )

    logger.info("")
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Files processed: {total_stats['files_processed']}")
    logger.info(f"Total runs removed: {total_stats['total_removed']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
