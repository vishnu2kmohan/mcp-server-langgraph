#!/usr/bin/env python3
"""
CI Script: Wall-Clock Sleep Time Budget Monitor

Monitors total wall-clock sleep time across test suite to prevent slow tests.

Purpose: Track and limit sleep time budget (Codex Finding #5)
Usage: python scripts/check_test_sleep_budget.py [--max-seconds 60]
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def find_sleep_calls():
    """
    Find all time.sleep() and asyncio.sleep() calls in test files.

    Returns:
        list: [(file_path, line_number, sleep_duration, context)]
    """
    test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

    sleep_calls = []

    for test_file in test_files:
        with open(test_file) as f:
            lines = f.readlines()

        for lineno, line in enumerate(lines, 1):
            # Match time.sleep(N) or asyncio.sleep(N)
            match = re.search(r"(?:time|asyncio)\.sleep\(([^)]+)\)", line)
            if match:
                sleep_arg = match.group(1)

                # Try to extract numeric value
                try:
                    # Handle simple numbers
                    if sleep_arg.replace(".", "").replace("+", "").replace("-", "").isdigit():
                        duration = float(sleep_arg)
                    # Handle expressions like "ttl_seconds + 0.5"
                    elif "+" in sleep_arg:
                        parts = sleep_arg.split("+")
                        # Conservative estimate: take the larger part if it's a number
                        max_part = max(p.strip() for p in parts if p.strip().replace(".", "").isdigit())
                        duration = float(max_part) if max_part else 1.0
                    else:
                        # Variable reference - estimate conservatively
                        duration = 5.0  # Conservative estimate for unknown variables
                except (ValueError, AttributeError):
                    duration = 5.0  # Conservative fallback

                context = line.strip()
                sleep_calls.append((test_file.relative_to(REPO_ROOT), lineno, duration, context))

    return sleep_calls


def main():
    """Main entry point for sleep budget check."""
    parser = argparse.ArgumentParser(description="Check test suite wall-clock sleep budget")
    parser.add_argument(
        "--max-seconds", type=int, default=60, help="Maximum total sleep time allowed in seconds (default: 60)"
    )
    parser.add_argument(
        "--warn-seconds", type=int, default=45, help="Warning threshold for sleep time in seconds (default: 45)"
    )
    parser.add_argument("--strict", action="store_true", help="Fail if budget exceeded (for CI enforcement)")

    args = parser.parse_args()

    # Find all sleep calls
    sleep_calls = find_sleep_calls()

    # Calculate total sleep time
    total_sleep = sum(duration for _, _, duration, _ in sleep_calls)

    # Print report
    print("=" * 70)
    print("Test Suite Wall-Clock Sleep Budget Report")
    print("=" * 70)
    print(f"Total sleep calls:     {len(sleep_calls)}")
    print(f"Total sleep time:      {total_sleep:.1f} seconds")
    print(f"Warning threshold:     {args.warn_seconds} seconds")
    print(f"Maximum budget:        {args.max_seconds} seconds")
    print("=" * 70)

    # Show top offenders
    if sleep_calls:
        print("\nTop 10 sleep calls by duration:")
        print("-" * 70)
        sorted_calls = sorted(sleep_calls, key=lambda x: x[2], reverse=True)[:10]
        for file_path, lineno, duration, context in sorted_calls:
            print(f"  {duration:5.1f}s  {file_path}:{lineno}")
            print(f"           {context[:60]}")

    # Check budget status
    print("\n" + "=" * 70)

    if total_sleep <= args.warn_seconds:
        print(f"✅ EXCELLENT: Sleep time ({total_sleep:.1f}s) well within budget ({args.max_seconds}s)")
        status = 0
    elif total_sleep <= args.max_seconds:
        margin = args.max_seconds - total_sleep
        print(f"⚠️  WARNING: Sleep time ({total_sleep:.1f}s) approaching budget ({args.max_seconds}s)")
        print(f"    Margin remaining: {margin:.1f}s")
        print("\n💡 Consider optimizing:")
        print("  - Replace time.sleep() with freezegun/time mocking")
        print("  - Use polling with shorter intervals instead of fixed sleeps")
        print("  - Reduce max_examples in Hypothesis property tests")
        status = 0
    else:
        excess = total_sleep - args.max_seconds
        print(f"❌ FAIL: Sleep time ({total_sleep:.1f}s) exceeds budget ({args.max_seconds}s)")
        print(f"    Over budget by: {excess:.1f}s")
        print("\n🔧 Required actions:")
        print("  - Reduce sleep durations in top offenders")
        print("  - Use time mocking (freezegun) for TTL/expiration tests")
        print("  - Replace sleep() with event-driven waits")
        status = 1 if args.strict else 0

    # Recommendations
    if total_sleep > args.warn_seconds:
        print("\n📚 Optimization Patterns:")
        print("  1. TTL tests: Use freezegun to advance time without sleeping")
        print("  2. Polling: Use retry decorators with exponential backoff")
        print("  3. Property tests: Reduce max_examples or deadline")
        print("  4. Integration tests: Mock time-based dependencies")

    return status


if __name__ == "__main__":
    sys.exit(main())
